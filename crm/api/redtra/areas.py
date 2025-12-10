from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import properties, utils


@frappe.whitelist()
@utils.require_jwt()
def list_areas() -> dict[str, Any]:
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	city = frappe.form_dict.get("city")

	filters: dict[str, Any] = {}
	if city:
		filters["city"] = city

	return utils.get_paginated_list(
		"Area",
		filters=filters,
		fields=[
			"name",
			"area_name",
			"city",
			"state",
			"country",
			"pincode",
			"latitude",
			"longitude",
		],
		page=page,
		page_size=page_size,
		order_by="area_name asc",
	)


@frappe.whitelist()
@utils.require_jwt()
def get_area(area_id: str) -> dict[str, Any]:
	area = frappe.get_doc("Area", area_id)
	area.check_permission("read")
	return area.as_dict()


@frappe.whitelist()
@utils.require_jwt()
def list_area_properties(area_id: str) -> dict[str, Any]:
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	min_price = frappe.form_dict.get("min_price")
	max_price = frappe.form_dict.get("max_price")

	filters: list[list[Any]] = [
		["Property", "status", "=", "Active"],
		["Property", "area", "=", area_id],
	]
	if min_price:
		filters.append(["Property", "price", ">=", float(min_price)])
	if max_price:
		filters.append(["Property", "price", "<=", float(max_price)])

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

