from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import split_emails, validate_email_address

from . import utils as redtra_utils


@frappe.whitelist()
def list_agencies_for_team_invite() -> list[dict[str, str]]:
	"""Agency picker for internal managers who have no Agent-linked agency (Invite team)."""
	from crm.api.redtra.billing import _is_internal_manager

	if not _is_internal_manager():
		frappe.throw(_("Only CRM managers can list agencies."), frappe.PermissionError)

	rows = frappe.get_all("Agency", fields=["name", "agency_name"], order_by="agency_name asc", limit=500)
	return [{"name": r.name, "agency_name": r.agency_name or r.name} for r in rows]


@frappe.whitelist(methods=["POST"])
def invite_agency_team_members(
	emails: str,
	agency_role: str = "Agent",
	agency_id: str | None = None,
) -> dict[str, Any]:
	"""Invite users to join an agency team (creates Agency Team Invitation rows)."""
	from crm.api.redtra.billing import _require_agency_access, get_agency_access_context

	if agency_role not in {"Agent", "Manager", "Admin"}:
		frappe.throw(_("Invalid agency role."))

	raw_id = (agency_id or "").strip() or None
	if raw_id:
		target_agency_id = raw_id
	else:
		target_agency_id = get_agency_access_context().get("agency")
	if not target_agency_id:
		frappe.throw(_("Select an agency to send invitations."), frappe.ValidationError)

	_context, agency_doc = _require_agency_access(agency_id=target_agency_id, require_team=True)

	email_string = validate_email_address(emails, throw=False)
	if not email_string:
		return {"invited": [], "skipped": []}

	email_list = split_emails(email_string)
	invited: list[str] = []
	skipped: list[dict[str, str]] = []

	for email in email_list:
		email = (email or "").strip().lower()
		if not email:
			continue
		if frappe.db.exists("Agent", {"user": email}):
			skipped.append({"email": email, "reason": "already_agent"})
			continue
		if frappe.db.exists(
			"Agency Team Invitation",
			{"email": email, "agency": agency_doc.name, "status": "Pending"},
		):
			skipped.append({"email": email, "reason": "already_invited"})
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Agency Team Invitation",
				"agency": agency_doc.name,
				"email": email,
				"agency_role": agency_role,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		invited.append(email)

	return {"invited": invited, "skipped": skipped}


@frappe.whitelist(allow_guest=True)
def accept_agency_team_invitation(key: str | None = None):
	"""Accept an agency invitation: ensure User + Agent role + Agent doc, then log in."""
	from crm.api.redtra.onboarding import _ensure_agency_user_permission, _next_temp_dfd_registration_id

	if not key:
		frappe.throw(_("Invalid or expired key"))

	names = frappe.get_all("Agency Team Invitation", filters={"key": key}, pluck="name", limit=1)
	if not names:
		frappe.throw(_("Invalid or expired key"))

	doc = frappe.get_doc("Agency Team Invitation", names[0])
	if doc.status != "Pending":
		frappe.throw(_("Invitation is no longer valid."))

	if frappe.db.exists("User", doc.email):
		user = frappe.get_doc("User", doc.email)
	else:
		first_name = doc.email.split("@")[0].title()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": doc.email,
				"first_name": first_name,
				"enabled": 1,
				"send_welcome_email": 0,
			}
		)
		user.flags.ignore_permissions = True
		user.insert()

	redtra_utils.ensure_agency_member_crm_roles(user.name, doc.agency_role)

	agent_name = frappe.db.get_value("Agent", {"user": user.name}, "name")
	if not agent_name:
		agent = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": user.name,
				"agency": doc.agency,
				"agency_role": doc.agency_role,
				"status": "Draft",
				"dfd_registration_id": _next_temp_dfd_registration_id(),
				"billable": 1,
			}
		)
		agent.flags.ignore_permissions = True
		agent.insert()
	else:
		agent_doc = frappe.get_doc("Agent", agent_name)
		if agent_doc.agency != doc.agency:
			frappe.throw(_("This user is already linked to another agency."))
		agent_doc.agency_role = doc.agency_role
		agent_doc.flags.ignore_permissions = True
		agent_doc.save()

	_ensure_agency_user_permission(user.name, doc.agency)

	doc.status = "Accepted"
	doc.accepted_at = frappe.utils.now()
	doc.flags.ignore_permissions = True
	doc.save()

	try:
		c = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Agency",
				"reference_name": doc.agency,
				"content": _("Team member invited: {0} accepted ({1}).").format(doc.email, doc.agency_role),
			}
		)
		c.flags.ignore_permissions = True
		c.insert()
	except Exception:
		pass

	frappe.local.login_manager.login_as(user.name)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/crm/onboarding"
