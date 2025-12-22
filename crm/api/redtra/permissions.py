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




