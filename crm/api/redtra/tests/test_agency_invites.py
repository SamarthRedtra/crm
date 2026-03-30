from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from crm.api.redtra import agency_invites, billing


class TestAgencyTeamInvites(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)
		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"Invite Agency {self.suffix}",
				"status": "Active",
				"billing_email": f"billing-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)

		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"team-admin-{self.suffix}@example.com",
				"first_name": "Team",
				"last_name": "Admin",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Agent"):
			self.user.add_roles("Agent")

		self.agent = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": self.user.name,
				"status": "Verified",
				"dfd_registration_id": f"DFD-INV-{self.suffix}",
				"agency": self.agency.name,
				"agency_role": "Admin",
				"billable": 1,
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Agency Team Invitation", filters={"agency": self.agency.name}, pluck="name"):
			if frappe.db.exists("Agency Team Invitation", name):
				frappe.delete_doc("Agency Team Invitation", name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agent", self.agent.name):
			frappe.delete_doc("Agent", self.agent.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agency", self.agency.name):
			frappe.delete_doc("Agency", self.agency.name, ignore_permissions=True, force=1)
		if frappe.db.exists("User", self.user.name):
			frappe.delete_doc("User", self.user.name, ignore_permissions=True, force=1)
		frappe.db.commit()

	def test_invite_creates_pending_invitation(self):
		frappe.set_user(self.user.name)
		out = agency_invites.invite_agency_team_members(
			emails=f"new-member-{self.suffix}@example.com",
			agency_role="Agent",
			agency_id=self.agency.name,
		)
		self.assertTrue(out.get("invited"))
		self.assertEqual(
			frappe.db.get_value(
				"Agency Team Invitation",
				{"email": f"new-member-{self.suffix}@example.com", "agency": self.agency.name},
				"status",
			),
			"Pending",
		)

	def test_invite_without_agency_id_uses_session_agency(self):
		frappe.set_user(self.user.name)
		out = agency_invites.invite_agency_team_members(
			emails=f"session-{self.suffix}@example.com",
			agency_role="Agent",
		)
		self.assertTrue(out.get("invited"))
		self.assertEqual(
			frappe.db.get_value(
				"Agency Team Invitation",
				{"email": f"session-{self.suffix}@example.com", "agency": self.agency.name},
				"agency",
			),
			self.agency.name,
		)

	@patch("frappe.sendmail")
	def test_internal_manager_invite_with_agency_id(self, _mock_send):
		manager = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"sales-mgr-{self.suffix}@example.com",
				"first_name": "Sales",
				"last_name": "Manager",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Sales Manager"):
			manager.add_roles("Sales Manager")
		frappe.db.commit()

		try:
			frappe.set_user(manager.name)
			out = agency_invites.invite_agency_team_members(
				emails=f"mgr-invite-{self.suffix}@example.com",
				agency_role="Manager",
				agency_id=self.agency.name,
			)
			self.assertTrue(out.get("invited"))
			self.assertEqual(
				frappe.db.get_value(
					"Agency Team Invitation",
					{"email": f"mgr-invite-{self.suffix}@example.com", "agency": self.agency.name},
					"agency_role",
				),
				"Manager",
			)
		finally:
			frappe.set_user("Administrator")
			for inv in frappe.get_all(
				"Agency Team Invitation",
				filters={"email": f"mgr-invite-{self.suffix}@example.com"},
				pluck="name",
			):
				frappe.delete_doc("Agency Team Invitation", inv, ignore_permissions=True, force=1)
			if frappe.db.exists("User", manager.name):
				frappe.delete_doc("User", manager.name, ignore_permissions=True, force=1)
			frappe.db.commit()

	def test_internal_manager_without_agency_must_select(self):
		manager = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"no-agency-mgr-{self.suffix}@example.com",
				"first_name": "No",
				"last_name": "Agency",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Sales Manager"):
			manager.add_roles("Sales Manager")
		frappe.db.commit()

		try:
			frappe.set_user(manager.name)
			with self.assertRaises(frappe.ValidationError):
				agency_invites.invite_agency_team_members(
					emails=f"fail-{self.suffix}@example.com",
					agency_role="Agent",
				)
		finally:
			frappe.set_user("Administrator")
			if frappe.db.exists("User", manager.name):
				frappe.delete_doc("User", manager.name, ignore_permissions=True, force=1)
			frappe.db.commit()

	@patch("frappe.sendmail")
	def test_accept_updates_role_when_agent_already_exists(self, _mock_send):
		email = f"existing-agent-{self.suffix}@example.com"
		invitee = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Existing",
				"last_name": "Agent",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Agent"):
			invitee.add_roles("Agent")

		existing = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": invitee.name,
				"status": "Draft",
				"dfd_registration_id": f"DFD-EX-{self.suffix}",
				"agency": self.agency.name,
				"agency_role": "Agent",
				"billable": 1,
			}
		).insert(ignore_permissions=True)

		inv = frappe.get_doc(
			{
				"doctype": "Agency Team Invitation",
				"agency": self.agency.name,
				"email": email,
				"agency_role": "Manager",
			}
		)
		inv.flags.ignore_permissions = True
		inv.insert()
		key = inv.key
		frappe.db.commit()

		try:
			with patch.object(frappe.local, "login_manager", MagicMock(), create=True):
				frappe.set_user("Guest")
				agency_invites.accept_agency_team_invitation(key=key)
			role = frappe.db.get_value("Agent", existing.name, "agency_role")
			self.assertEqual(role, "Manager")
			from frappe.core.doctype.user_permission.user_permission import user_permission_exists

			self.assertTrue(user_permission_exists(invitee.name, "Agency", self.agency.name, None))
		finally:
			frappe.set_user("Administrator")
			if frappe.db.exists("Agency Team Invitation", inv.name):
				frappe.delete_doc("Agency Team Invitation", inv.name, ignore_permissions=True, force=1)
			if frappe.db.exists("Agent", existing.name):
				frappe.delete_doc("Agent", existing.name, ignore_permissions=True, force=1)
			if frappe.db.exists("User", invitee.name):
				frappe.delete_doc("User", invitee.name, ignore_permissions=True, force=1)
			frappe.db.commit()


class TestAgencyAddonCustomRateLock(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)
		settings = frappe.get_single("Agency Billing Settings")
		settings.billing_enabled = 1
		settings.flags.ignore_permissions = True
		settings.save()

		self.addon = frappe.get_doc(
			{
				"doctype": "Billing Addon",
				"addon_name": f"Lock Addon {self.suffix}",
				"pricing_model": "Daily Fixed",
				"rate": 40,
				"currency": "AED",
				"active": 1,
			}
		).insert(ignore_permissions=True)

		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"Lock Agency {self.suffix}",
				"status": "Active",
				"billing_email": f"billing-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)
		self.agency.append(
			"billing_addons",
			{"addon": self.addon.name, "quantity": 1, "enabled": 1, "custom_rate": 99},
		)
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		self.agent_user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"lock-agent-{self.suffix}@example.com",
				"first_name": "Lock",
				"last_name": "Agent",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Agent"):
			self.agent_user.add_roles("Agent")

		self.agent = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": self.agent_user.name,
				"status": "Verified",
				"dfd_registration_id": f"DFD-LCK-{self.suffix}",
				"agency": self.agency.name,
				"agency_role": "Admin",
				"billable": 1,
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		if frappe.db.exists("Agent", self.agent.name):
			frappe.delete_doc("Agent", self.agent.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agency", self.agency.name):
			frappe.delete_doc("Agency", self.agency.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Billing Addon", self.addon.name):
			frappe.delete_doc("Billing Addon", self.addon.name, ignore_permissions=True, force=1)
		if frappe.db.exists("User", self.agent_user.name):
			frappe.delete_doc("User", self.agent_user.name, ignore_permissions=True, force=1)
		frappe.db.commit()

	def test_non_manager_cannot_change_custom_rate_via_api(self):
		frappe.set_user(self.agent_user.name)
		payload = {
			"billing_addons": [
				{
					"addon": self.addon.name,
					"quantity": 1,
					"enabled": 1,
					"custom_rate": 1,
				}
			]
		}
		import json

		billing.update_current_agency_profile(agency_id=self.agency.name, data=json.dumps(payload))
		row = frappe.get_doc("Agency", self.agency.name).billing_addons[0]
		self.assertEqual(float(row.custom_rate or 0), 99.0)
