from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, strip_html
from frappe.query_builder import DocType, functions as fn

from . import properties, utils

SUMMARY_FIELDS = [
	"name",
	"developer_name",
	"status",
	"city",
	"state",
	"country",
	"logo",
	"website",
]


@frappe.whitelist(allow_guest=True)
def list_developers() -> dict[str, Any]:
	with utils.maybe_authenticate_jwt():
		page = cint(frappe.form_dict.get("page") or 1)
		page_size = cint(frappe.form_dict.get("page_size") or 20)
		status = (frappe.form_dict.get("status") or "").strip()
		city = (frappe.form_dict.get("city") or "").strip()
		search = (frappe.form_dict.get("search") or "").strip()
		include_stats = _coerce_bool(frappe.form_dict.get("include_property_stats"))
		property_ids = properties._get_list_param("property_ids")
		requires_property_filter = bool(property_ids)
		has_properties_only = _coerce_bool(frappe.form_dict.get("has_properties"))

		filters: list[list[Any]] = []
		if status:
			filters.append(["Developer", "status", "=", status])
		if city:
			filters.append(["Developer", "city", "=", city])
		if search:
			filters.append(["Developer", "developer_name", "like", f"%{search}%"])

		property_counts: dict[str, int] = {}
		restrict, agent_id = properties.resolve_agent_scope()

		if restrict or requires_property_filter or has_properties_only or include_stats:
			property_filters: dict[str, Any] = {"status": "Active"}
			if property_ids:
				property_filters["name"] = ["in", property_ids]
			if restrict and agent_id:
				property_filters["agent"] = agent_id

			prop = DocType("Property")
			query = (
				frappe.qb.from_(prop)
				.select(prop.developer, fn.Count(prop.name).as_("property_count"))
				.groupby(prop.developer)
			)
			for key, value in property_filters.items():
				if isinstance(value, (list, tuple)) and len(value) == 2 and value[0] == "in":
					query = query.where(getattr(prop, key).isin(value[1]))
				else:
					query = query.where(getattr(prop, key) == value)
			for entry in query.run(as_dict=True):
				developer_name = entry.get("developer")
				if not developer_name:
					continue
				property_counts[developer_name] = int(entry.get("property_count") or 0)

			if has_properties_only or requires_property_filter or restrict:
				if not property_counts:
					return {
						"items": [],
						"page": page,
						"page_size": page_size,
						"total_items": 0,
						"total_pages": 0,
					}
				filters.append(["Developer", "name", "in", list(property_counts.keys())])

		result = utils.get_paginated_list(
			"Developer",
			filters=filters,
			fields=SUMMARY_FIELDS,
			page=page,
			page_size=page_size,
			order_by="developer_name asc",
		)

		items: list[dict[str, Any]] = []
		for row in result["items"]:
			summary = _serialize_developer_summary(row)
			if include_stats or row.get("name") in property_counts:
				summary["property_count"] = property_counts.get(row.get("name"), 0)
			items.append(summary)

		result["items"] = items
		return result


@frappe.whitelist(allow_guest=True)
def get_developer(developer_id: str) -> dict[str, Any]:
	with utils.maybe_authenticate_jwt() as user:
		doc = frappe.get_doc("Developer", developer_id)

		if doc.status != "Active":
			if not user:
				frappe.throw(_("Developer is not active."), frappe.PermissionError)
			if "System Manager" not in frappe.get_roles(user):
				frappe.throw(_("Developer is not active."), frappe.PermissionError)

		restrict, agent_id = properties.resolve_agent_scope()
		property_filters: dict[str, Any] = {"status": "Active", "developer": doc.name}
		if restrict and agent_id:
			property_filters["agent"] = agent_id

		property_count = frappe.db.count("Property", property_filters)

		data = _serialize_developer_detail(doc)
		data["property_count"] = property_count
		return data


@frappe.whitelist()
@utils.require_jwt(roles={"System Manager"})
def create_developer() -> dict[str, Any]:
	data = utils.get_request_json(["developer_name"])
	status = (data.get("status") or "Active").strip() or "Active"
	if status not in {"Active", "Inactive"}:
		frappe.throw(_("Invalid status value."), frappe.ValidationError)

	doc = frappe.get_doc(
		{
			"doctype": "Developer",
			"developer_name": data["developer_name"],
			"status": status,
			"email": data.get("email"),
			"phone": data.get("phone"),
			"website": data.get("website"),
			"address_line1": data.get("address_line1"),
			"address_line2": data.get("address_line2"),
			"city": data.get("city"),
			"state": data.get("state"),
			"country": data.get("country"),
			"pincode": data.get("pincode"),
			"logo": data.get("logo"),
			"description": data.get("description"),
		}
	)
	# System Manager can bypass standard permissions for API-based provisioning.
	doc.insert(ignore_permissions=True)

	frappe.response.http_status_code = 201
	return _serialize_developer_detail(doc)


@frappe.whitelist(allow_guest=True)
def list_developer_properties(developer_id: str) -> dict[str, Any]:
	with utils.maybe_authenticate_jwt():
		page = cint(frappe.form_dict.get("page") or 1)
		page_size = cint(frappe.form_dict.get("page_size") or 20)

		filters: list[list[Any]] = [
			["Property", "status", "=", "Active"],
			["Property", "developer", "=", developer_id],
		]

		restrict, agent_id = properties.resolve_agent_scope()
		if restrict:
			if not agent_id:
				frappe.throw(_("Agent profile not found."), frappe.PermissionError)
			filters.append(["Property", "agent", "=", agent_id])

		result = utils.get_paginated_list(
			"Property",
			filters=filters,
			fields=properties.SUMMARY_FIELDS,
			page=page,
			page_size=page_size,
			order_by="modified desc",
		)
		result["items"] = [properties.serialize_property_summary(row) for row in result["items"]]
		return result


def _serialize_developer_summary(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": row.get("name"),
		"name": row.get("developer_name"),
		"status": row.get("status"),
		"city": row.get("city"),
		"state": row.get("state"),
		"country": row.get("country"),
		"logo": row.get("logo"),
		"website": row.get("website"),
		"location": _build_location(row.get("city"), row.get("state"), row.get("country")),
	}


def _serialize_developer_detail(doc) -> dict[str, Any]:
	return {
		"id": doc.name,
		"name": doc.developer_name,
		"status": doc.status,
		"email": doc.email,
		"phone": doc.phone,
		"website": doc.website,
		"address_line1": doc.address_line1,
		"address_line2": doc.address_line2,
		"city": doc.city,
		"state": doc.state,
		"country": doc.country,
		"pincode": doc.pincode,
		"logo": doc.logo,
		"description": doc.description,
		"description_not_formatted": strip_html(doc.description) if doc.description else None,
		"location": _build_location(doc.city, doc.state, doc.country),
	}


def _build_location(city: str | None, state: str | None, country: str | None) -> str | None:
	components = []
	for value in (city, state, country):
		text = (value or "").strip()
		if text and text not in components:
			components.append(text)
	return ", ".join(components) if components else None


def _coerce_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return False
	if isinstance(value, (int, float)):
		return bool(value)
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "y", "on"}
	return False
