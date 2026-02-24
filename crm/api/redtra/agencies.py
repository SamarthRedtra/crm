from __future__ import annotations

from typing import Any

import frappe
import math
from frappe import _
from frappe.utils import cint

from . import utils

SUMMARY_FIELDS = [
	"name",
	"agency_name",
	"description",
	"status",
	"city",
	"state",
	"country",
	"logo",
	"website",
	"phone",
	"email",
	"brn_id",
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

	agency_ids = [row["name"] for row in items]
	agency_stats = _get_agency_stats(agency_ids)

	return {
		"items": [
			{
				**_serialize_agency_summary(row),
				"active_count": agency_stats.get(row["name"], {}).get("active", 0),
				"sale_count": agency_stats.get(row["name"], {}).get("sale", 0),
				"rent_count": agency_stats.get(row["name"], {}).get("rent", 0),
			}
			for row in items
		],
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

	return _serialize_agency_detail(doc)


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

	agent_ids = [row["name"] for row in items]
	from . import agents
	property_counts = agents._get_agent_property_counts(agent_ids)
	
	# Get lead counts for these agents
	lead_counts = {}
	if agent_ids:
		lead_result = frappe.db.get_all(
			"CRM Lead",
			filters={"agent_id": ["in", agent_ids]},
			fields=["agent_id", {"COUNT": "*", "as": "count"}],
			group_by="agent_id"
		)
		lead_counts = {row.get("agent_id"): row.get("count") for row in lead_result}

	return {
		"items": [
			{
				**agents._serialize_agent_summary(row),
				"property_count": property_counts.get(row["name"], 0),
				"lead_count": lead_counts.get(row["name"], 0),
			}
			for row in items
		],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


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
		fields=[
			"listing_type",
			{"COUNT": "name", "as": "total_count"},
			{"SUM": "price", "as": "total_price"},
		],
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

	total_leads = frappe.db.count("CRM Lead", {"agency": agency_id})

	return {
		"agency_id": agency_id,
		"total_active_listings": total_active_listings,
		"total_sales": total_sales,
		"total_rent": total_rent,
		"total_leads": total_leads,
	}


def _serialize_agency_detail(doc) -> dict[str, Any]:
	properties_list = []
	try:
		# Find all agents belonging to the agency
		agent_ids = frappe.get_all(
			"Agent",
			filters={"agency": doc.name},
			pluck="name",
			ignore_permissions=True,
		)
		
		# Fetch all active properties:
		# 1. Assigned to agents of this agency
		# 2. Linked to this agency via Off Plan multi-select
		from . import properties
		
		placeholders = ",".join(["%s"] * len(agent_ids)) if agent_ids else "''"
		
		# Build select fields with alias 'p'
		select_fields = ", ".join([f"p.{f}" for f in properties.SUMMARY_FIELDS])
		
		query = f"""
			SELECT DISTINCT {select_fields}
			FROM `tabProperty` p
			LEFT JOIN `tabProperty Agency` pa ON p.name = pa.parent
			WHERE p.status = 'Active' 
			AND (
				{'p.agent IN ({placeholders})' if agent_ids else '1=0'}
				OR 
				(p.completion_status = 'Off-plan' AND pa.agency = %s)
			)
			ORDER BY p.modified DESC
		""".format(placeholders=placeholders)
		
		params = tuple(agent_ids) + (doc.name,)
		
		result = frappe.db.sql(query, params, as_dict=True)
		properties_list = [properties.serialize_property_summary(row) for row in result]
	except Exception:
		pass

	# Get stats for the single agency
	stats = _get_agency_stats([doc.name]).get(doc.name, {})
	
	# Get top property types and areas
	property_types = []
	service_areas = []
	if agent_ids:
		# Use group by on fetched property list or a separate query
		# Separate query is more robust for large sets
		type_result = frappe.db.get_all(
			"Property",
			filters={"agent": ["in", agent_ids], "status": "Active"},
			fields=["property_type", {"COUNT": "name", "as": "count"}],
			group_by="property_type",
			order_by="count desc",
			limit=5
		)
		property_types = [row.get("property_type") for row in type_result if row.get("property_type")]

		area_result = frappe.db.get_all(
			"Property",
			filters={"agent": ["in", agent_ids], "status": "Active"},
			fields=["area", {"COUNT": "name", "as": "count"}],
			group_by="area",
			order_by="count desc",
			limit=5
		)
		service_area_ids = [row.get("area") for row in area_result if row.get("area")]
		if service_area_ids:
			area_names = frappe.get_all(
				"Area",
				filters={"name": ["in", service_area_ids]},
				fields=["name", "area_name"]
			)
			name_map = {row["name"]: row["area_name"] for row in area_names}
			service_areas = [name_map.get(aid, aid) for aid in service_area_ids]

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
		"brn_id": doc.brn_id,
		"location": _build_location(doc.city, doc.state, doc.country),
		"total_listings": stats.get("total", 0),
		"active_listings": stats.get("active", 0),
		"sale_listings": stats.get("sale", 0),
		"rent_listings": stats.get("rent", 0),
		"property_types": property_types,
		"service_areas": service_areas,
		"properties": properties_list,
	}


@frappe.whitelist(allow_guest=True)
def list_agency_properties(agency_id: str) -> dict[str, Any]:
	"""Public API to list properties belonging to an agency."""
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page = max(1, page)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size

	frappe.set_user("Administrator")
	if not frappe.db.exists("Agency", {"name": agency_id}):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	agent_ids = frappe.get_all(
		"Agent",
		filters={"agency": agency_id},
		pluck="name",
		ignore_permissions=True,
	)

	# Build logic to fetch properties from agents OR off-plan linkage
	placeholders = ",".join(["%s"] * len(agent_ids)) if agent_ids else "''"
	
	where_clause = f"""
		p.status = 'Active' 
		AND (
			{'p.agent IN ({placeholders})' if agent_ids else '1=0'}
			OR 
			(p.completion_status = 'Off-plan' AND pa.agency = %s)
		)
	""".format(placeholders=placeholders)
	
	params = tuple(agent_ids) + (agency_id,)

	# Count total
	count_sql = f"""
		SELECT COUNT(DISTINCT p.name)
		FROM `tabProperty` p
		LEFT JOIN `tabProperty Agency` pa ON p.name = pa.parent
		WHERE {where_clause}
	"""
	
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		total_items = frappe.db.sql(count_sql, params)[0][0]
	finally:
		frappe.set_user(original_user)
		
	if total_items == 0:
		return {
			"items": [],
			"page": page,
			"page_size": page_size,
			"total_items": 0,
			"total_pages": 0,
		}

	# Fetch items
	fields = [
		"name", "title", "listing_type", "property_type", "property_category",
		"price", "currency", "bedrooms", "bathrooms", "area_sqft",
		"city", "area", "developer", "agent", "furnishing_status",
		"state", "country", "primary_image", "status", "is_featured", "featured_until"
	]
	select_fields = ", ".join([f"p.{f}" for f in fields])
	
	data_sql = f"""
		SELECT DISTINCT {select_fields}
		FROM `tabProperty` p
		LEFT JOIN `tabProperty Agency` pa ON p.name = pa.parent
		WHERE {where_clause}
		ORDER BY p.modified DESC
		LIMIT %s OFFSET %s
	"""
	
	items = frappe.db.sql(data_sql, params + (page_size, start), as_dict=True)


	
	total_pages = math.ceil(total_items / page_size) if page_size else 0

	from . import properties

	return {
		"items": [properties.serialize_property_summary(row) for row in items],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
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
			"brn_id": data.get("brn_id"),
		}
	)
	doc.insert(ignore_permissions=True)

	frappe.response.http_status_code = 201
	return _serialize_agency_detail(doc)


def _serialize_agency_summary(doc: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": row.get("name") if (row := doc) else None,
		"name": doc.get("agency_name"),
		"description": doc.get("description"),
		"status": doc.get("status"),
		"city": doc.get("city"),
		"state": doc.get("state"),
		"country": doc.get("country"),
		"logo": doc.get("logo"),
		"website": doc.get("website"),
		"phone": doc.get("phone"),
		"email": doc.get("email"),
		"brn_id": doc.get("brn_id"),
		"location": _build_location(doc.get("city"), doc.get("state"), doc.get("country")),
	}


def get_agency_details(agency_id: str | None, include_stats: bool = False) -> dict[str, Any] | None:
	"""Helper function to get agency details for embedding in agent responses"""
	if not agency_id:
		return None
	
	try:
		doc = frappe.get_cached_doc("Agency", agency_id)
		if doc.status != "Active":
			return None
		
		res = _serialize_agency_summary(doc.as_dict())
		if include_stats:
			stats = _get_agency_stats([agency_id]).get(agency_id, {})
			res.update({
				"total_listings": stats.get("total", 0),
				"active_listings": stats.get("active", 0),
				"sale_listings": stats.get("sale", 0),
				"rent_listings": stats.get("rent", 0),
			})
		return res
	except frappe.DoesNotExistError:
		return None


def _get_agency_stats(agency_ids: list[str]) -> dict[str, dict[str, int]]:
	if not agency_ids:
		return {}

	stats: dict[str, dict[str, int]] = {
		aid: {"total": 0, "active": 0, "sale": 0, "rent": 0} for aid in agency_ids
	}

	placeholders = ",".join(["%s"] * len(agency_ids))
	
	# Union query to get unique property-agency pairs from both:
	# 1. Properties assigned to agents of the agency
	# 2. Properties linked to the agency via 'Off Plan' multi-select
	query = f"""
		SELECT agency, 
			   COUNT(*) as total,
			   SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active,
			   SUM(CASE WHEN status = 'Active' AND listing_type = 'Buy' THEN 1 ELSE 0 END) as sale,
			   SUM(CASE WHEN status = 'Active' AND listing_type = 'Rent' THEN 1 ELSE 0 END) as rent
		FROM (
			SELECT DISTINCT p.name, a.agency, p.status, p.listing_type
			FROM `tabProperty` p
			JOIN `tabAgent` a ON p.agent = a.name
			WHERE a.agency IN ({placeholders})
			
			UNION
			
			SELECT DISTINCT p.name, pa.agency, p.status, p.listing_type
			FROM `tabProperty` p
			JOIN `tabProperty Agency` pa ON p.name = pa.parent
			WHERE pa.agency IN ({placeholders}) AND p.completion_status = 'Off-plan'
		) as unique_listings
		WHERE status = 'Active'
		GROUP BY agency
	"""
	
	# We pass the agency_ids tuple twice because of the two SELECTs in UNION
	# Update: Actually the WHERE clause is inside the subqueries, so we need to pass it twice.
	# But wait, my query construction above has placeholders in both subqueries.
	# So I need to pass (agency_ids + agency_ids).
	
	result = frappe.db.sql(query, tuple(agency_ids) * 2, as_dict=True)

	for row in result:
		aid = row.get("agency")
		if aid in stats:
			stats[aid] = {
				"total": int(row.get("total") or 0),
				"active": int(row.get("active") or 0),
				"sale": int(row.get("sale") or 0),
				"rent": int(row.get("rent") or 0),
			}
	return stats


def _build_location(city: str | None, state: str | None, country: str | None) -> str | None:
	components = []
	for value in (city, state, country):
		text = (value or "").strip()
		if text and text not in components:
			components.append(text)
	return ", ".join(components) if components else None
