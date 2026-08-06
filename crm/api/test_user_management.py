import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from crm.api import user as user_api


class TestAgencyUserManagementScope(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.global_search_patch = patch("frappe.model.document.update_global_search")
		self.global_search_patch.start()
		self.suffix = frappe.generate_hash(length=8)
		self.agency = self.make_agency("Primary")
		self.other_agency = self.make_agency("Other")
		self.agency_admin = self.make_user("agency-admin")
		self.local_agent_user = self.make_user("local-agent")
		self.foreign_agent_user = self.make_user("foreign-agent")
		self.crm_manager = self.make_user("crm-manager")

		self.agency_admin.add_roles("Agency Admin", "Agent")
		self.local_agent_user.add_roles("Agent")
		self.foreign_agent_user.add_roles("Agent")
		self.crm_manager.add_roles("Sales Manager")

		self.agents = [
			self.make_agent(self.agency_admin.name, self.agency, "Admin"),
			self.make_agent(self.local_agent_user.name, self.agency, "Agent"),
			self.make_agent(self.foreign_agent_user.name, self.other_agency, "Agent"),
		]
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for agent in self.agents:
			if frappe.db.exists("Agent", agent.name):
				frappe.delete_doc("Agent", agent.name, ignore_permissions=True, force=1)
		for agency in [self.agency, self.other_agency]:
			if frappe.db.exists("Agency", agency.name):
				frappe.delete_doc("Agency", agency.name, ignore_permissions=True, force=1)
		for member in [
			self.agency_admin,
			self.local_agent_user,
			self.foreign_agent_user,
			self.crm_manager,
		]:
			if frappe.db.exists("User", member.name):
				frappe.delete_doc("User", member.name, ignore_permissions=True, force=1)
		frappe.db.commit()
		self.global_search_patch.stop()

	def make_agency(self, label):
		return frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"{label} scope {self.suffix}",
				"status": "Active",
				"email": f"{label.lower()}-{self.suffix}@example.com",
				"phone": "0500000000",
				"whatsapp_number": "0500000000",
				"brn_id": f"BRN-{label}-{self.suffix}",
				"rera_id": f"RERA-{label}-{self.suffix}",
				"billing_email": f"billing-{label.lower()}-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)

	def make_user(self, prefix):
		with patch("frappe.enqueue"):
			return frappe.get_doc(
				{
					"doctype": "User",
					"email": f"{prefix}-{self.suffix}@example.com",
					"first_name": prefix.title(),
					"enabled": 1,
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)

	def make_agent(self, user, agency, agency_role):
		return frappe.get_doc(
			{
				"doctype": "Agent",
				"user": user,
				"agency": agency.name,
				"agency_role": agency_role,
				"status": "Verified",
				"dfd_registration_id": f"DFD-SCOPE-{frappe.generate_hash(length=8)}",
				"phone": "0500000000",
				"whatsapp_number": "0500000000",
				"billable": 1,
			}
		).insert(ignore_permissions=True)

	def test_agency_manager_sees_only_its_agents_and_cannot_manage_others(self):
		frappe.set_user(self.agency_admin.name)
		candidates = user_api.get_existing_user_candidates()
		candidate_names = {row.name for row in candidates}

		self.assertIn(self.local_agent_user.name, candidate_names)
		self.assertNotIn(self.foreign_agent_user.name, candidate_names)

		with self.assertRaises(frappe.PermissionError):
			user_api.add_existing_users(
				users=json.dumps([self.foreign_agent_user.name]),
				role="Sales User",
			)
		with self.assertRaises(frappe.PermissionError):
			user_api.update_user_role(self.foreign_agent_user.name, "Sales User")
		with self.assertRaises(frappe.PermissionError):
			user_api.remove_user(self.foreign_agent_user.name)

	def test_crm_manager_keeps_global_candidate_access(self):
		frappe.set_user(self.crm_manager.name)
		candidates = user_api.get_existing_user_candidates()
		candidate_names = {row.name for row in candidates}

		self.assertIn(self.local_agent_user.name, candidate_names)
		self.assertIn(self.foreign_agent_user.name, candidate_names)
