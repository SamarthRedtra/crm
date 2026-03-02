from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import properties, utils

SUMMARY_FIELDS = [
	"name",
	"agency_name",
	"status",
	"city",
	"state",
	"country",
	"logo",
	"website",
	"phone",
	"email",
]


@frappe.whitelist(allow_guest=True)
def list_agencies() -> dict[str, Any]:
	"""Public API to list agencies - no authentication required"""
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	status = (frappe.form_dict.get("status") or "").strip()
	search = (frappe.form_dict.get("search") or "").strip()

	page = max(1, page)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size

	filters: list[list[Any]] = []
	if status:
		filters.append(["Agency", "status", "=", status])
	else:
		filters.append(["Agency", "status", "=", "Active"])

	if search:
		filters.append(["Agency", "agency_name", "like", f"%{search}%"])

	items = frappe.get_all(
		"Agency",
		filters=filters,
		fields=SUMMARY_FIELDS,
		start=start,
		limit=page_size,
		order_by="agency_name asc",
		ignore_permissions=True,
	)

	# Bypass permissions for count
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		total_items = frappe.db.count("Agency", filters, cache=False)
	finally:
		frappe.set_user(original_user)
	total_pages = (total_items + page_size - 1) // page_size if page_size else 0

	return {
		"items": [_serialize_agency_summary(row) for row in items],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


@frappe.whitelist(allow_guest=True)
def get_agency(agency_id: str) -> dict[str, Any]:
	"""Public API to get agency details - no authentication required"""
	frappe.set_user("Administrator")
	agency_name = frappe.db.get_value("Agency", {"name": agency_id}, "name")
	if not agency_name:
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)
		
	doc = frappe.get_doc("Agency", agency_name)
	doc.flags.ignore_permissions = True

	if doc.status != "Active":
		frappe.throw(_("Agency is not active."), frappe.PermissionError)

	detail = _serialize_agency_detail(doc)
	agency_summary = _build_agency_property_stats(agency_id)
	detail.update(agency_summary)
	detail["properties"] = _get_agency_properties(agency_id, limit=50)
	detail["service_areas"] = _get_agency_service_areas(agency_id)
	return detail


@frappe.whitelist(allow_guest=True)
def get_agency_profile(agency_id: str) -> dict[str, Any]:
	"""Public API to get full agency profile with metadata."""
	frappe.set_user("Administrator")
	agency_name = frappe.db.get_value("Agency", {"name": agency_id}, "name")
	if not agency_name:
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	doc = frappe.get_doc("Agency", agency_name)
	doc.flags.ignore_permissions = True

	if doc.status != "Active":
		frappe.throw(_("Agency is not active."), frappe.PermissionError)

	detail = _serialize_agency_detail(doc)
	detail["metadata"] = {
		"creation": doc.creation,
		"modified": doc.modified,
		"owner": doc.owner,
		"modified_by": doc.modified_by,
	}
	return detail


@frappe.whitelist(allow_guest=True)
def list_agency_agents(agency_id: str) -> dict[str, Any]:
	"""Public API to list agents belonging to an agency."""
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page = max(1, page)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size

	frappe.set_user("Administrator")
	if not frappe.db.exists("Agency", {"name": agency_id}):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	filters: list[list[Any]] = [["Agent", "agency", "=", agency_id]]
	items = frappe.get_all(
		"Agent",
		filters=filters,
		fields=[
			"name",
			"full_name",
			"status",
			"phone",
			"whatsapp_number",
			"bio",
			"profile_image",
			"agency",
		],
		start=start,
		limit=page_size,
		order_by="modified desc",
		ignore_permissions=True,
	)

	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		total_items = frappe.db.count("Agent", filters, cache=False)
	finally:
		frappe.set_user(original_user)
	total_pages = (total_items + page_size - 1) // page_size if page_size else 0

	from . import agents

	return {
		"items": [agents._serialize_agent_summary(row) for row in items],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


@frappe.whitelist(allow_guest=True)
def list_agency_properties(agency_id: str) -> dict[str, Any]:
	"""Public API to list active properties for an agency."""
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page = max(1, page)
	page_size = max(1, min(page_size, 100))

	frappe.set_user("Administrator")
	if not frappe.db.exists("Agency", {"name": agency_id}):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	property_ids = _get_agency_property_ids(agency_id)
	if not property_ids:
		return {
			"items": [],
			"page": page,
			"page_size": page_size,
			"total_items": 0,
			"total_pages": 0,
		}

	result = utils.get_paginated_list(
		"Property",
		filters={"status": "Active", "name": ["in", list(property_ids)]},
		fields=properties.SUMMARY_FIELDS,
		page=page,
		page_size=page_size,
		order_by="modified desc",
	)
	result["items"] = [properties.serialize_property_summary(row) for row in result["items"]]
	return result


@frappe.whitelist(allow_guest=True)
def get_agency_analytics(agency_id: str) -> dict[str, Any]:
	"""Public API to get agency analytics."""
	frappe.set_user("Administrator")
	agency_name = frappe.db.get_value("Agency", {"name": agency_id}, "name")
	if not agency_name:
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	agency_doc = frappe.get_doc("Agency", agency_name)
	agency_doc.flags.ignore_permissions = True
	if agency_doc.status != "Active":
		frappe.throw(_("Agency is not active."), frappe.PermissionError)

	agent_ids = frappe.get_all(
		"Agent",
		filters={"agency": agency_id},
		pluck="name",
		ignore_permissions=True,
	)

	if not agent_ids:
		return {
			"agency_id": agency_id,
			"total_active_listings": 0,
			"total_sales": 0.0,
			"total_rent": 0.0,
			"total_leads": 0,
		}

	property_stats = frappe.db.get_all(
		"Property",
		filters={"status": "Active", "agent": ["in", agent_ids]},
		fields=["listing_type", "count(name) as total_count", "sum(price) as total_price"],
		group_by="listing_type",
	)

	total_active_listings = 0
	total_sales = 0.0
	total_rent = 0.0
	for row in property_stats:
		listing_type = (row.get("listing_type") or "").strip()
		count = int(row.get("total_count") or 0)
		total_active_listings += count
		total_price = float(row.get("total_price") or 0)
		if listing_type == "Buy":
			total_sales += total_price
		elif listing_type == "Rent":
			total_rent += total_price

	total_leads = frappe.db.count("Property Appointment", {"agent": ["in", agent_ids]})

	return {
		"agency_id": agency_id,
		"total_active_listings": total_active_listings,
		"total_sales": total_sales,
		"total_rent": total_rent,
		"total_leads": total_leads,
	}


@frappe.whitelist()
@utils.require_jwt(roles={"System Manager"})
def create_agency() -> dict[str, Any]:
	"""Create a new agency - System Manager only"""
	data = utils.get_request_json(["agency_name"])
	status = (data.get("status") or "Active").strip() or "Active"
	if status not in {"Active", "Inactive"}:
		frappe.throw(_("Invalid status value."), frappe.ValidationError)

	doc = frappe.get_doc(
		{
			"doctype": "Agency",
			"agency_name": data["agency_name"],
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
	doc.insert(ignore_permissions=True)

	frappe.response.http_status_code = 201
	return _serialize_agency_detail(doc)


def _serialize_agency_summary(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": row.get("name"),
		"name": row.get("agency_name"),
		"status": row.get("status"),
		"city": row.get("city"),
		"state": row.get("state"),
		"country": row.get("country"),
		"logo": row.get("logo"),
		"website": row.get("website"),
		"phone": row.get("phone"),
		"email": row.get("email"),
		"location": _build_location(row.get("city"), row.get("state"), row.get("country")),
	}


def _serialize_agency_detail(doc) -> dict[str, Any]:
	return {
		"id": doc.name,
		"name": doc.agency_name,
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


def get_agency_details(agency_id: str | None, include_stats: bool = False) -> dict[str, Any] | None:
	"""Helper function to get agency details for embedding in agent responses"""
	if not agency_id:
		return None
	
	try:
		doc = frappe.get_cached_doc("Agency", agency_id)
		if doc.status != "Active":
			return None
		data = _serialize_agency_summary(doc.as_dict())
		if include_stats:
			data.update(_build_agency_property_stats(agency_id))
		return data
	except frappe.DoesNotExistError:
		return None


def _get_agency_property_ids(agency_id: str) -> set[str]:
	agent_ids = frappe.get_all(
		"Agent",
		filters={"agency": agency_id},
		pluck="name",
		ignore_permissions=True,
	)
	property_ids: set[str] = set()
	if agent_ids:
		property_ids.update(
			frappe.get_all(
				"Property",
				filters={"status": "Active", "agent": ["in", agent_ids]},
				pluck="name",
				ignore_permissions=True,
			)
		)
	off_plan_property_ids = frappe.get_all(
		"Property Agency",
		filters={"agency": agency_id},
		pluck="parent",
		ignore_permissions=True,
	)
	property_ids.update(off_plan_property_ids or [])
	return property_ids


def _get_agency_properties(agency_id: str, limit: int = 50) -> list[dict[str, Any]]:
	property_ids = _get_agency_property_ids(agency_id)
	if not property_ids:
		return []
	rows = frappe.get_all(
		"Property",
		filters={"status": "Active", "name": ["in", list(property_ids)]},
		fields=properties.SUMMARY_FIELDS,
		order_by="modified desc",
		limit=limit,
		ignore_permissions=True,
	)
	return [properties.serialize_property_summary(row) for row in rows]


def _build_agency_property_stats(agency_id: str) -> dict[str, Any]:
	property_ids = _get_agency_property_ids(agency_id)
	if not property_ids:
		return {
			"total_listings": 0,
			"active_listings": 0,
			"sale_listings": 0,
			"rent_listings": 0,
		}

	stats_rows = frappe.db.get_all(
		"Property",
		filters={"status": "Active", "name": ["in", list(property_ids)]},
		fields=["listing_type", "count(name) as total"],
		group_by="listing_type",
	)
	active_listings = 0
	sale_listings = 0
	rent_listings = 0
	for row in stats_rows:
		count = int(row.get("total") or 0)
		active_listings += count
		if row.get("listing_type") == "Buy":
			sale_listings += count
		elif row.get("listing_type") == "Rent":
			rent_listings += count
	return {
		"total_listings": active_listings,
		"active_listings": active_listings,
		"sale_listings": sale_listings,
		"rent_listings": rent_listings,
	}


def _get_agency_service_areas(agency_id: str) -> list[str]:
	property_ids = _get_agency_property_ids(agency_id)
	if not property_ids:
		return []
	areas = frappe.db.get_all(
		"Property",
		filters={"status": "Active", "name": ["in", list(property_ids)]},
		fields=["area"],
		group_by="area",
	)
	area_names: list[str] = []
	for row in areas:
		area_id = row.get("area")
		if not area_id:
			continue
		area_name = frappe.db.get_value("Area", area_id, "area_name") or area_id
		if area_name not in area_names:
			area_names.append(area_name)
	return area_names


def _build_location(city: str | None, state: str | None, country: str | None) -> str | None:
	components = []
	for value in (city, state, country):
		text = (value or "").strip()
		if text and text not in components:
			components.append(text)
	return ", ".join(components) if components else None
