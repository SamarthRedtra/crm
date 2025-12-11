from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import properties, utils

SUMMARY_FIELDS = [
	"name",
	"full_name",
	"status",
	"phone",
	"whatsapp_number",
	"bio",
	"profile_image",
]


@frappe.whitelist(allow_guest=True)
def list_agents() -> dict[str, Any]:
	with utils.maybe_authenticate_jwt():
		page = cint(frappe.form_dict.get("page") or 1)
		page_size = cint(frappe.form_dict.get("page_size") or 20)
		status = (frappe.form_dict.get("status") or "").strip()
		search = (frappe.form_dict.get("search") or "").strip()

	page = max(1, page)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size

	filters: list[list[Any]] = []
	if status:
		filters.append(["Agent", "status", "=", status])
	else:
		filters.append(["Agent", "status", "=", "Verified"])

	if search:
		filters.append(["Agent", "full_name", "like", f"%{search}%"])

	items = frappe.get_all(
		"Agent",
		filters=filters,
		fields=SUMMARY_FIELDS,
		start=start,
		limit=page_size,
		order_by="modified desc",
		ignore_permissions=True,
	)

	total_items = frappe.db.count("Agent", filters, cache=True, ignore_permissions=True)
	total_pages = (total_items + page_size - 1) // page_size if page_size else 0

	property_counts = _get_agent_property_counts([row["name"] for row in items])

	return {
		"items": [
			{
				**_serialize_agent_summary(row),
				"property_count": property_counts.get(row["name"], 0),
			}
			for row in items
		],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


@frappe.whitelist(allow_guest=True)
def get_agent(agent_id: str) -> dict[str, Any]:
	with utils.maybe_authenticate_jwt() as user:
		doc = frappe.get_doc("Agent", agent_id)

		if doc.status != "Verified":
			if not user or "System Manager" not in frappe.get_roles(user):
				frappe.throw(_("Agent is not verified."), frappe.PermissionError)

	return _serialize_agent_detail(doc)


def _serialize_agent_summary(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": row.get("name"),
		"name": row.get("full_name") or row.get("name"),
		"status": row.get("status"),
		"bio": row.get("bio"),
		"phone": row.get("phone"),
		"whatsapp_number": row.get("whatsapp_number"),
		"profile_image": row.get("profile_image"),
	}


def _serialize_agent_detail(doc) -> dict[str, Any]:
	properties_list = frappe.get_all(
		"Property",
		filters={"status": "Active", "agent": doc.name},
		fields=properties.SUMMARY_FIELDS,
		order_by="modified desc",
		limit=50,
		ignore_permissions=True,
	)

	return {
		"id": doc.name,
		"name": doc.full_name or doc.name,
		"status": doc.status,
		"bio": doc.bio,
		"phone": doc.phone,
		"whatsapp_number": doc.whatsapp_number,
		"profile_image": doc.profile_image,
		"property_count": len(properties_list),
		"properties": [properties.serialize_property_summary(row) for row in properties_list],
	}


def _get_agent_property_counts(agent_ids: list[str]) -> dict[str, int]:
	if not agent_ids:
		return {}

	counts: dict[str, int] = {}
	for row in frappe.get_all(
		"Property",
		filters={"status": "Active", "agent": ["in", agent_ids]},
		fields=["agent", "count(name) as total"],
		group_by="agent",
		ignore_permissions=True,
	):
		agent = row.get("agent")
		if agent:
			counts[agent] = int(row.get("total") or 0)
	return counts
