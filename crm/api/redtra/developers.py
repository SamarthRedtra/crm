from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import utils

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
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	status = (frappe.form_dict.get("status") or "").strip()
	city = (frappe.form_dict.get("city") or "").strip()
	search = (frappe.form_dict.get("search") or "").strip()

	filters: list[list[Any]] = []
	if status:
		filters.append(["Developer", "status", "=", status])
	if city:
		filters.append(["Developer", "city", "=", city])
	if search:
		filters.append(["Developer", "developer_name", "like", f"%{search}%"])

	result = utils.get_paginated_list(
		"Developer",
		filters=filters,
		fields=SUMMARY_FIELDS,
		page=page,
		page_size=page_size,
		order_by="developer_name asc",
	)

	result["items"] = [_serialize_developer_summary(row) for row in result["items"]]
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

		return _serialize_developer_detail(doc)


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
		"location": _build_location(doc.city, doc.state, doc.country),
	}


def _build_location(city: str | None, state: str | None, country: str | None) -> str | None:
	components = []
	for value in (city, state, country):
		text = (value or "").strip()
		if text and text not in components:
			components.append(text)
	return ", ".join(components) if components else None
