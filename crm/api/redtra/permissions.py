from __future__ import annotations

import frappe
from frappe import _

from . import utils


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

	agent_id = frappe.db.get_value("Agent", {"user": user}, "name")
	if not agent_id:
		return "1=0"

	return f"`tabProperty`.`agent` = {frappe.db.escape(agent_id)}"


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

	agent_id = frappe.db.get_value("Agent", {"user": user}, "name")
	if not agent_id:
		frappe.throw(_("Agent profile not found."), frappe.PermissionError)

	return doc.agent == agent_id


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



