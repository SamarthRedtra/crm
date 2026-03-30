from __future__ import annotations

import frappe
from frappe import _

# Agency roles that may list all Property rows tied to any Agent in the same agency.
AGENCY_WIDE_PROPERTY_ROLES = ("Admin", "Manager")


def has_agency_leadership_role(user: str | None = None) -> bool:
	"""Agent doc has agency_role Admin or Manager (dashboard access, manager charts)."""
	user = user or frappe.session.user
	profile = _get_agent_profile_for_user(user)
	if not profile or not profile.get("name"):
		return False
	role = (profile.get("agency_role") or "Agent").strip()
	return role in AGENCY_WIDE_PROPERTY_ROLES


def has_agency_wide_property_access(user: str | None = None) -> bool:
	"""
	Same scope as the agency-wide branch of Property list permission:
	Admin/Manager with an agency sees every listing from agents on that agency.
	"""
	user = user or frappe.session.user
	profile = _get_agent_profile_for_user(user)
	if not profile or not profile.get("name"):
		return False
	agency = profile.get("agency")
	role = (profile.get("agency_role") or "Agent").strip()
	return bool(agency and role in AGENCY_WIDE_PROPERTY_ROLES)


def get_property_sql_scope_for_user(user: str | None = None) -> tuple[str, dict]:
	"""
	Extra WHERE fragment for `tabProperty` queries (dashboard counts, reports).
	Mirrors `get_property_permission_query` rules.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return "", {}
	roles = set(frappe.get_roles(user))
	if "System Manager" in roles:
		return "", {}
	if "Agent" not in roles:
		return "", {}

	profile = _get_agent_profile_for_user(user)
	if not profile or not profile.get("name"):
		return " AND 1=0", {}

	agent_id = profile["name"]
	agency = profile.get("agency")
	role = (profile.get("agency_role") or "Agent").strip()

	if agency and role in AGENCY_WIDE_PROPERTY_ROLES:
		esc = frappe.db.escape(agency)
		return (
			f" AND `tabProperty`.`agent` IN (SELECT `name` FROM `tabAgent` WHERE `agency` = {esc})",
			{},
		)
	esc_agent = frappe.db.escape(agent_id)
	return f" AND `tabProperty`.`agent` = {esc_agent}", {}


def _get_agent_profile_for_user(user: str) -> dict | None:
	"""Current user's Agent row: name, agency, agency_role."""
	return frappe.db.get_value(
		"Agent",
		{"user": user},
		["name", "agency", "agency_role"],
		as_dict=True,
	)


def _property_agent_in_same_agency(property_agent: str | None, agency: str | None) -> bool:
	if not property_agent or not agency:
		return False
	agent_agency = frappe.db.get_value("Agent", property_agent, "agency")
	return bool(agent_agency and agent_agency == agency)


def get_property_permission_query(user: str) -> str | None:
	if not user or user in {"Guest"}:
		return "1=0"

	if user == "Administrator":
		return None

	user_roles = set(frappe.get_roles(user))
	if "System Manager" in user_roles:
		return None

	if "Agent" not in user_roles:
		return None

	scope, _ = get_property_sql_scope_for_user(user)
	if not scope:
		return None
	s = scope.strip()
	if s.upper().startswith("AND"):
		s = s[3:].strip()
	return s


def has_property_permission(doc, user: str) -> bool:
	if not user or user in {"Guest"}:
		return False

	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))
	if "System Manager" in user_roles:
		return True

	if "Agent" not in user_roles:
		return True

	profile = _get_agent_profile_for_user(user)
	if not profile or not profile.get("name"):
		frappe.throw(_("Agent profile not found."), frappe.PermissionError)

	agent_id = profile["name"]
	if getattr(doc, "agent", None) == agent_id:
		return True

	agency = profile.get("agency")
	role = (profile.get("agency_role") or "Agent").strip()
	if agency and role in AGENCY_WIDE_PROPERTY_ROLES:
		return _property_agent_in_same_agency(getattr(doc, "agent", None), agency)

	return False


def _is_internal_manager(user: str) -> bool:
	if user == "Administrator":
		return True
	roles = set(frappe.get_roles(user))
	return bool({"System Manager", "Sales Manager"} & roles)


def _get_agent_agency(user: str) -> str | None:
	return frappe.db.get_value("Agent", {"user": user}, "agency")


def _get_agency_filter_query(doctype: str, user: str) -> str | None:
	if not user or user in {"Guest"}:
		return "1=0"
	if _is_internal_manager(user):
		return None
	if "Agent" not in set(frappe.get_roles(user)):
		return "1=0"
	agency_name = _get_agent_agency(user)
	if not agency_name:
		return "1=0"
	return f"`tab{doctype}`.`agency` = {frappe.db.escape(agency_name)}"


def _has_agency_scoped_permission(doc, user: str) -> bool:
	if not user or user in {"Guest"}:
		return False
	if _is_internal_manager(user):
		return True
	agency_name = _get_agent_agency(user)
	if not agency_name:
		frappe.throw(_("Agent profile not found."), frappe.PermissionError)
	return getattr(doc, "agency", None) == agency_name


def get_agency_billing_invoice_permission_query(user: str) -> str | None:
	return _get_agency_filter_query("Agency Billing Invoice", user)


def has_agency_billing_invoice_permission(doc, user: str) -> bool:
	return _has_agency_scoped_permission(doc, user)


def get_agency_billing_accrual_permission_query(user: str) -> str | None:
	return _get_agency_filter_query("Agency Billing Accrual", user)


def has_agency_billing_accrual_permission(doc, user: str) -> bool:
	return _has_agency_scoped_permission(doc, user)


def has_agency_permission(doc, user: str, ptype: str | None = None) -> bool:
	del ptype
	if not user or user in {"Guest"}:
		return False
	if _is_internal_manager(user):
		return True
	agency_name = _get_agent_agency(user)
	if not agency_name:
		return False
	return getattr(doc, "name", None) == agency_name


def has_agency_billing_permission(doc, user: str, ptype: str | None = None) -> bool:
	del ptype
	return _has_agency_scoped_permission(doc, user)



