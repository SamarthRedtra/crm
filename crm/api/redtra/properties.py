from __future__ import annotations

import json
from datetime import datetime
import math
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder import DocType, functions as fn
from frappe.utils import cint, get_datetime, getdate, now_datetime, strip_html
from pypika import Order

from . import featured_logs, reviews, utils

# Agent review rows embedded under agent.ratings.recent_reviews in list responses
LIST_PROPERTY_AGENT_REVIEW_LIMIT = 25

SUMMARY_FIELDS = [
	"name",
	"title",
	"listing_type",
	"completion_status",
	"property_type",
	"property_category",
	"price",
	"currency",
	"bedrooms",
	"bathrooms",
	"area_sqft",
	"city",
	"area",
	"developer",
	"agent",
	"furnishing_status",
	"state",
	"country",
	"primary_image",
	"status",
	"is_featured",
	"is_sold",
	"is_rented",
	"rent_type",
	"featured_until",
	"description",
	"trakheesi_permit_number",
	"trakheesi_qr_code",
	"zone_name",
	"handover_quarter",
	"handover_year",
]

TITLE_MAX_LETTERS = 50


@frappe.whitelist(allow_guest=True)
def list_properties() -> dict[str, Any]:
	with utils.maybe_authenticate_jwt():
		page = max(1, cint(frappe.form_dict.get("page") or 1))
		page_size = cint(frappe.form_dict.get("page_size") or 20)
		page_size = max(1, min(page_size, 100))
		offset = (page - 1) * page_size

		property_dt = DocType("Property")
		area_dt = DocType("Area")
		developer_dt = DocType("Developer")

		conditions = [property_dt.status == "Active"]

		listing_type = (frappe.form_dict.get("listing_type") or "").strip()
		if listing_type:
			conditions.append(property_dt.listing_type == listing_type)

		# Completion status (All/Ready/Off-Plan): only for Buy listings; hidden for Rent
		completion_status = (frappe.form_dict.get("completion_status") or "").strip()
		if completion_status and completion_status != "All" and listing_type != "Rent":
			conditions.append(property_dt.completion_status == completion_status)

		# Buy: filter by is_sold; is_rented filter hidden in UI
		if listing_type == "Buy":
			if (is_sold := frappe.form_dict.get("is_sold")) is not None:
				conditions.append(property_dt.is_sold == int(_coerce_bool(is_sold)))

		# Rent: filter by is_rented and rent_type; is_sold and completion_status hidden in UI
		if listing_type == "Rent":
			if (is_rented := frappe.form_dict.get("is_rented")) is not None:
				conditions.append(property_dt.is_rented == int(_coerce_bool(is_rented)))
			rent_type_filter = (frappe.form_dict.get("rent_type") or "").strip()
			if rent_type_filter:
				conditions.append(property_dt.rent_type == rent_type_filter)

		property_types = _get_list_param("property_types") or _get_list_param("property_type")
		if property_types:
			conditions.append(property_dt.property_type.isin(property_types))

		property_categories = _get_list_param("property_category") or _get_list_param("property_categories")
		if property_categories:
			conditions.append(property_dt.property_category.isin(property_categories))

		min_price = _get_float_param("min_price")
		if min_price is not None:
			conditions.append(property_dt.price >= min_price)
		max_price = _get_float_param("max_price")
		if max_price is not None:
			conditions.append(property_dt.price <= max_price)

		bedroom_values = _get_int_list_param("bedrooms")
		if bedroom_values:
			conditions.append(property_dt.bedrooms.isin(bedroom_values))

		min_bedrooms = _get_int_param("min_bedrooms")
		if min_bedrooms is not None:
			conditions.append(property_dt.bedrooms >= min_bedrooms)
		max_bedrooms = _get_int_param("max_bedrooms")
		if max_bedrooms is not None:
			conditions.append(property_dt.bedrooms <= max_bedrooms)

		bathroom_values = _get_int_list_param("bathrooms")
		if bathroom_values:
			conditions.append(property_dt.bathrooms.isin(bathroom_values))

		min_bathrooms = _get_int_param("min_bathrooms")
		if min_bathrooms is not None:
			conditions.append(property_dt.bathrooms >= min_bathrooms)
		max_bathrooms = _get_int_param("max_bathrooms")
		if max_bathrooms is not None:
			conditions.append(property_dt.bathrooms <= max_bathrooms)

		min_area = (
			_get_float_param("min_area")
			or _get_float_param("min_area_sqft")
			or _get_float_param("min_area_sq_ft")
		)
		if min_area is not None:
			conditions.append(property_dt.area_sqft >= min_area)
		max_area = (
			_get_float_param("max_area")
			or _get_float_param("max_area_sqft")
			or _get_float_param("max_area_sq_ft")
		)
		if max_area is not None:
			conditions.append(property_dt.area_sqft <= max_area)

		area_ids = _get_list_param("area_id") or _get_list_param("area_ids")
		if area_ids:
			conditions.append(property_dt.area.isin(area_ids))

		developer_ids = _get_list_param("developer_id") or _get_list_param("developer")
		if developer_ids:
			conditions.append(property_dt.developer.isin(developer_ids))

		property_ids = _get_list_param("id") or _get_list_param("property_id") or _get_list_param("property_ids")
		if property_ids:
			conditions.append(property_dt.name.isin(property_ids))

		agent = (frappe.form_dict.get("agent") or "").strip()
		if agent:
			conditions.append(property_dt.agent == agent)

		furnishing_values = _get_list_param("furnishing") or _get_list_param("furnishings")
		if furnishing_values:
			conditions.append(property_dt.furnishing_status.isin(furnishing_values))

		if (furnished := frappe.form_dict.get("furnished")) is not None:
			is_furnished_bool = _coerce_bool(furnished)
			conditions.append(property_dt.furnishing_status == "Furnished" if is_furnished_bool else property_dt.furnishing_status != "Furnished")

		if (is_furnished := frappe.form_dict.get("is_furnished")) is not None:
			is_furnished_flag = _coerce_bool(is_furnished)
			conditions.append(property_dt.furnishing_status == "Furnished" if is_furnished_flag else property_dt.furnishing_status != "Furnished")

		amenities = _get_list_param("amenities")
		if amenities:
			property_ids_with_amenities = _get_property_ids_with_all_amenities(amenities)
			if not property_ids_with_amenities:
				return {
					"items": [],
					"page": page,
					"page_size": page_size,
					"total_items": 0,
					"total_pages": 0,
				}
			conditions.append(property_dt.name.isin(list(property_ids_with_amenities)))

		if (is_featured := frappe.form_dict.get("is_featured")) is not None:
			is_featured_flag = int(_coerce_bool(is_featured))
			conditions.append(property_dt.is_featured == is_featured_flag)
			if is_featured_flag:
				conditions.append(property_dt.featured_until >= now_datetime())

		location = (frappe.form_dict.get("location") or "").strip()
		if location:
			location_like = f"%{location}%"
			location_condition = (
				property_dt.city.like(location_like)
				| property_dt.state.like(location_like)
				| property_dt.country.like(location_like)
				| property_dt.address_line1.like(location_like)
				| property_dt.address_line2.like(location_like)
				| property_dt.title.like(location_like)
				| property_dt.description.like(location_like)
			)

			area_matches = frappe.get_all(
				"Area",
				filters=[["area_name", "like", location_like]],
				pluck="name",
			)
			if area_matches:
				location_condition = location_condition | property_dt.area.isin(area_matches)
			conditions.append(location_condition)

		# Note: This is a public endpoint (allow_guest=True), so we don't restrict by agent scope
		# All active properties should be visible to everyone
		# Agent scope restriction is only applied when creating/updating properties (not listing)
		# If you want to filter by a specific agent, use the "agent" query parameter above

		summary_query = (
			frappe.qb.from_(property_dt)
			.left_join(area_dt)
			.on(property_dt.area == area_dt.name)
			.left_join(developer_dt)
			.on(property_dt.developer == developer_dt.name)
			.select(
				property_dt.name.as_("name"),
				property_dt.title.as_("title"),
				property_dt.listing_type.as_("listing_type"),
				property_dt.completion_status.as_("completion_status"),
				property_dt.property_type.as_("property_type"),
				property_dt.property_category.as_("property_category"),
				property_dt.price.as_("price"),
				property_dt.currency.as_("currency"),
				property_dt.bedrooms.as_("bedrooms"),
				property_dt.bathrooms.as_("bathrooms"),
				property_dt.area_sqft.as_("area_sqft"),
				property_dt.city.as_("city"),
				property_dt.area.as_("area"),
				property_dt.developer.as_("developer"),
				property_dt.agent.as_("agent"),
				property_dt.furnishing_status.as_("furnishing_status"),
				property_dt.state.as_("state"),
				property_dt.country.as_("country"),
				property_dt.primary_image.as_("primary_image"),
				property_dt.status.as_("status"),
				property_dt.is_featured.as_("is_featured"),
				property_dt.is_sold.as_("is_sold"),
				property_dt.is_rented.as_("is_rented"),
				property_dt.rent_type.as_("rent_type"),
				property_dt.featured_until.as_("featured_until"),
				property_dt.description.as_("description"),
				property_dt.trakheesi_permit_number.as_("trakheesi_permit_number"),
				property_dt.trakheesi_qr_code.as_("trakheesi_qr_code"),
				property_dt.zone_name.as_("zone_name"),
				property_dt.handover_quarter.as_("handover_quarter"),
				property_dt.handover_year.as_("handover_year"),
				area_dt.area_name.as_("area_name"),
				developer_dt.developer_name.as_("developer_name"),
			)
		)

		for condition in conditions:
			summary_query = summary_query.where(condition)

		summary_query = (
			summary_query.orderby(property_dt.modified, order=Order.desc)
			.offset(offset)
			.limit(page_size)
		)

		rows = summary_query.run(as_dict=True)

		count_query = frappe.qb.from_(property_dt).select(fn.Count(property_dt.name))
		for condition in conditions:
			count_query = count_query.where(condition)

		total_items = count_query.run()[0][0]
		total_pages = math.ceil(total_items / page_size) if page_size else 0

		return {
			"items": [serialize_property_summary(row) for row in rows],
			"page": page,
			"page_size": page_size,
			"total_items": total_items,
			"total_pages": total_pages,
		}
	
@frappe.whitelist(allow_guest=True)
def get_property(property_id: str) -> dict[str, Any]:
	with utils.maybe_authenticate_jwt() as user:
		doc = frappe.get_doc("Property", property_id)
		if not user and doc.status != "Active":
			frappe.throw(_("Property is not active."), frappe.PermissionError)

		_enforce_agent_property_scope(doc)
		return serialize_property_detail(doc)


@frappe.whitelist()
@utils.require_jwt(roles={"Agent", "System Manager"})
def create_property() -> dict[str, Any]:
	data = utils.get_request_json(
		["title", "listing_type", "property_type", "price", "currency"]
	)
	current_user = utils.get_current_user()
	user_roles = set(frappe.get_roles(current_user))

	# C-13: Title letter-count validation
	title = data.get("title", "").strip()
	_validate_title_letter_count(title)

	# C-07: Role-aware Trakheesi validation
	if "System Manager" not in user_roles:
		if not data.get("trakheesi_permit_number"):
			frappe.throw(_("Trakheesi Permit Number is mandatory."), frappe.ValidationError)
		if not data.get("trakheesi_qr_code"):
			frappe.throw(_("Trakheesi QR Code is mandatory."), frappe.ValidationError)

	agent_name = data.get("agent") or frappe.db.get_value("Agent", {"user": current_user}, "name")
	if not agent_name:
		frappe.throw(_("You must be a verified agent to create properties."), frappe.PermissionError)

	is_featured = int(_coerce_bool(data.get("is_featured"))) if "is_featured" in data else 0
	if data.get("featured_until") and "is_featured" not in data:
		is_featured = 1
	featured_until = _normalize_featured_until(data.get("featured_until"), is_featured)

	doc = frappe.get_doc(
		{
			"doctype": "Property",
			"title": data["title"],
			"listing_type": data["listing_type"],
			"property_type": data["property_type"],
			"property_category": data.get("property_category"),
			"price": data["price"],
			"currency": data["currency"],
			"bedrooms": data.get("bedrooms"),
			"bathrooms": data.get("bathrooms"),
			"furnishing_status": data.get("furnishing_status") or data.get("furnishing"),
			"area_sqft": data.get("area_sqft"),
			"area": data.get("area_id"),
			"developer": data.get("developer_id") or data.get("developer"),
			"address_line1": data.get("address_line1"),
			"address_line2": data.get("address_line2"),
			"city": data.get("city"),
			"state": data.get("state"),
			"country": data.get("country"),
			"pincode": data.get("pincode"),
			"latitude": data.get("latitude"),
			"longitude": data.get("longitude"),
			"description": data.get("description"),
			"trakheesi_permit_number": data.get("trakheesi_permit_number"),
			"trakheesi_qr_code": data.get("trakheesi_qr_code"),
			"zone_name": data.get("zone_name"),
			"agent": agent_name,
			"primary_image": data.get("primary_image"),
			"is_featured": is_featured,
			"featured_until": featured_until,
		}
	)
	doc.flags.featured_log_source = "API"

	for amenity in data.get("amenities") or []:
		if isinstance(amenity, dict):
			value = amenity.get("amenity_name") or amenity.get("amenity")
		else:
			value = amenity
		if amenity_name := _ensure_amenity_master(value):
			doc.append("amenities", {"amenity_name": amenity_name})

	for image in data.get("gallery") or []:
		if isinstance(image, dict):
			doc.append(
				"gallery",
				{
					"image": image.get("image"),
					"caption": image.get("caption"),
					"sort_order": image.get("sort_order"),
				},
			)

	doc.insert(ignore_permissions=True)
	frappe.response.http_status_code = 201
	return serialize_property_detail(doc)


@frappe.whitelist()
@utils.require_jwt(roles={"Agent", "System Manager"})
def update_property(property_id: str) -> dict[str, Any]:
	data = utils.get_request_json()
	doc = frappe.get_doc("Property", property_id)

	_validate_property_owner(doc)

	is_featured_value = (
		int(_coerce_bool(data.get("is_featured")))
		if "is_featured" in data
		else doc.is_featured
	)
	if data.get("featured_until") and "is_featured" not in data:
		is_featured_value = 1
	# C-13: Title letter-count validation (if updated)
	if "title" in data:
		title = data.get("title", "").strip()
		_validate_title_letter_count(title)

	# C-07: Role-aware Trakheesi validation for update
	current_user = utils.get_current_user()
	user_roles = set(frappe.get_roles(current_user))
	if "System Manager" not in user_roles:
		if "trakheesi_permit_number" in data and not data.get("trakheesi_permit_number"):
			frappe.throw(_("Trakheesi Permit Number is mandatory."), frappe.ValidationError)
		if "trakheesi_qr_code" in data and not data.get("trakheesi_qr_code"):
			frappe.throw(_("Trakheesi QR Code is mandatory."), frappe.ValidationError)
		
		# Also ensure they aren't cleared if not in data (though doc.update handles it, explicit is better if we want to enforce presence)
		if not data.get("trakheesi_permit_number") and not doc.trakheesi_permit_number:
			frappe.throw(_("Trakheesi Permit Number is mandatory."), frappe.ValidationError)
		if not data.get("trakheesi_qr_code") and not doc.trakheesi_qr_code:
			frappe.throw(_("Trakheesi QR Code is mandatory."), frappe.ValidationError)

	featured_until = _normalize_featured_until(data.get("featured_until"), is_featured_value)

	doc.update(
		{
			"title": data.get("title") or doc.title,
			"listing_type": data.get("listing_type") or doc.listing_type,
			"property_type": data.get("property_type") or doc.property_type,
			"property_category": data.get("property_category", doc.property_category),
			"price": data.get("price", doc.price),
			"currency": data.get("currency") or doc.currency,
			"bedrooms": data.get("bedrooms", doc.bedrooms),
			"bathrooms": data.get("bathrooms", doc.bathrooms),
			"furnishing_status": data.get(
				"furnishing_status", data.get("furnishing", doc.furnishing_status)
			),
			"area_sqft": data.get("area_sqft", doc.area_sqft),
			"area": data.get("area_id", doc.area),
			"developer": (
				data["developer_id"]
				if "developer_id" in data
				else data.get("developer", doc.developer)
			),
			"address_line1": data.get("address_line1", doc.address_line1),
			"address_line2": data.get("address_line2", doc.address_line2),
			"city": data.get("city", doc.city),
			"state": data.get("state", doc.state),
			"country": data.get("country", doc.country),
			"pincode": data.get("pincode", doc.pincode),
			"latitude": data.get("latitude", doc.latitude),
			"longitude": data.get("longitude", doc.longitude),
			"description": data.get("description", doc.description),
			"trakheesi_permit_number": data.get("trakheesi_permit_number", doc.trakheesi_permit_number),
			"trakheesi_qr_code": data.get("trakheesi_qr_code", doc.trakheesi_qr_code),
			"zone_name": data.get("zone_name", doc.zone_name),
			"is_featured": is_featured_value,
			"featured_until": featured_until,
			"status": data.get("status", doc.status),
		}
	)
	doc.flags.featured_log_source = "API"

	if "amenities" in data:
		doc.set("amenities", [])
		for amenity in data.get("amenities") or []:
			value = amenity.get("amenity_name") if isinstance(amenity, dict) else amenity
			if amenity_name := _ensure_amenity_master(value):
				doc.append("amenities", {"amenity_name": amenity_name})

	if "gallery" in data:
		doc.set("gallery", [])
		for image in data.get("gallery") or []:
			doc.append(
				"gallery",
				{
					"image": image.get("image"),
					"caption": image.get("caption"),
					"sort_order": image.get("sort_order"),
				},
			)

	doc.save(ignore_permissions=True)
	return serialize_property_detail(doc)


@frappe.whitelist()
@utils.require_jwt(roles={"Agent", "System Manager"})
def deactivate_property(property_id: str) -> dict[str, Any]:
	doc = frappe.get_doc("Property", property_id)
	_validate_property_owner(doc)
	doc.status = "Inactive"
	doc.save(ignore_permissions=True)
	frappe.response.http_status_code = 204
	return {}


@frappe.whitelist()
@utils.require_jwt()
def get_whatsapp_link(property_id: str) -> dict[str, str]:
	doc = frappe.get_doc("Property", property_id)
	agent = frappe.get_doc("Agent", doc.agent)
	number = _get_alora_whatsapp_number() or agent.whatsapp_number or agent.phone
	if not number:
		frappe.throw(_("WhatsApp number is not configured."))

	message = _("Hi, I am interested in {0}").format(doc.property_code or doc.name)
	clean_number = str(number).replace("+", "").replace(" ", "")
	link = f"https://wa.me/{clean_number}?text={quote(message)}"
	return {"whatsapp_chat_link": link}


def serialize_property_summary(row: dict[str, Any]) -> dict[str, Any]:
	area_name = row.get("area_name")
	if area_name is None and row.get("area"):
		area_name = frappe.db.get_value("Area", row["area"], "area_name")

	developer_id = row.get("developer")
	developer = _get_developer_profile(developer_id)

	agent_id = row.get("agent")
	agent = None
	agency_details = None
	if agent_id:
		try:
			agent_data = frappe.db.get_value(
				"Agent",
				agent_id,
				[
					"name",
					"full_name",
					"user",
					"phone",
					"whatsapp_number",
					"profile_image",
					"status",
					"agency",
					"trakheesi_permit_number",
					"trakheesi_qr_code",
					"zone_name",
					"email",
				],
				as_dict=True,
			)
			if agent_data:
				agency_id = agent_data.get("agency")
				if agency_id:
					try:
						from . import agencies
						agency_details = agencies.get_agency_details(agency_id)
					except Exception:
						agency_details = None
				whatsapp_number_for_links = _get_alora_whatsapp_number() or agent_data.get("whatsapp_number") or agent_data.get("phone")
				whatsapp_link = _build_whatsapp_link(whatsapp_number_for_links)
				agent = {
					"id": agent_data.get("name"),
					"name": agent_data.get("full_name") or agent_data.get("user"),
					"phone": agent_data.get("phone"),
					"whatsapp_number": whatsapp_number_for_links,
					"whatsapp_link": whatsapp_link,
					"profile_image": agent_data.get("profile_image"),
					"status": agent_data.get("status"),
					"email": agent_data.get("email"),
					"trakheesi_permit_number": agent_data.get("trakheesi_permit_number"),
					"trakheesi_qr_code": agent_data.get("trakheesi_qr_code"),
					"zone_name": agent_data.get("zone_name"),
				}
				try:
					agent["ratings"] = reviews.get_agent_rating_stats(
						agent_data.get("name"),
						include_review_items=True,
						review_items_limit=LIST_PROPERTY_AGENT_REVIEW_LIMIT,
					)
				except Exception:
					agent["ratings"] = reviews.empty_agent_rating_summary()
		except Exception:
			# If agent doesn't exist or error, leave as None
			pass

	location = _build_location_label(
		area_name,
		row.get("city"),
		row.get("state"),
		row.get("country"),
	)

	property_id = row.get("name")
	amenities = []
	gallery = []
	
	if property_id:
		# Fetch amenities with icons
		amenity_rows = frappe.get_all(
			"Property Amenity",
			filters={"parent": property_id},
			fields=["amenity_name"],
		)
		amenities = []
		for amenity_row in amenity_rows:
			amenity_name = amenity_row.amenity_name
			amenity_doc = None
			try:
				amenity_doc = frappe.get_doc("Amenity", amenity_name)
			except Exception:
				pass
			
			# Icon field now stores Lucide icon name as string
			icon_name = None
			if amenity_doc and hasattr(amenity_doc, "icon") and amenity_doc.icon:
				icon_name = amenity_doc.icon
			
			amenity_dict = {
				"name": amenity_doc.amenity_name if amenity_doc else amenity_name,
				"icon": icon_name,  # Returns Lucide icon name (e.g., "home", "wifi", "car")
			}
			amenities.append(amenity_dict)
		
		# Fetch gallery
		gallery_rows = frappe.get_all(
			"Property Image",
			filters={"parent": property_id},
			fields=["image", "caption", "sort_order"],
			order_by="sort_order asc",
		)
		gallery = [
			{"image": row.image, "caption": row.caption, "sort_order": row.sort_order}
			for row in gallery_rows
		]

	featured_until = row.get("featured_until")
	featured_until_value, featured_remaining = _get_featured_timer(featured_until)
	completion_status = row.get("completion_status")
	completion_status_key = (completion_status or "").strip().lower()

	payment_plan = []
	project_units = []
	if property_id and completion_status_key in {"off-plan", "offplan"}:
		payment_plan_rows = frappe.get_all(
			"Off Plan Payment Installment",
			filters={"parent": property_id},
			fields=["payment_plan", "milestone", "percentage", "idx"],
			order_by="idx asc",
		)
		payment_plan = [
			{"payment_plan": r.payment_plan, "milestone": r.milestone, "percentage": r.percentage, "idx": r.idx}
			for r in payment_plan_rows
		]

		project_units_rows = frappe.get_all(
			"Project Unit",
			filters={"parent": property_id},
			fields=["property_type", "num_bedrooms", "layout_type", "size", "bathrooms", "floor_plan", "idx"],
			order_by="idx asc",
		)
		project_units = _group_project_units(project_units_rows)

	return {
		"id": property_id,
		"title": row.get("title"),
		"listing_type": row.get("listing_type"),
		"completion_status": row.get("completion_status"),
		"property_type": row.get("property_type"),
		"property_category": row.get("property_category"),
		"price": row.get("price"),
		"currency": row.get("currency"),
		"bedrooms": row.get("bedrooms"),
		"bathrooms": row.get("bathrooms"),
		"area_sqft": row.get("area_sqft"),
		"city": row.get("city"),
		"area": row.get("area"),
		"area_name": area_name,
		"is_featured": bool(row.get("is_featured")),
		"featured_until": featured_until_value,
		"featured_remaining_seconds": featured_remaining,
		"trakheesi_permit_number": row.get("trakheesi_permit_number"),
		"trakheesi_qr_code": row.get("trakheesi_qr_code"),
		"zone_name": row.get("zone_name"),
		"developer": developer,
		"developer_id": developer["id"] if developer else None,
		"developer_name": developer["name"] if developer else None,
		"agent": agent,
		"agency": agency_details,
		"is_sold": bool(row.get("is_sold")),
		"is_rented": bool(row.get("is_rented")),
		"rent_type": row.get("rent_type"),
		"location": location,
		"primary_image_url": row.get("primary_image"),
		"furnishing_status": row.get("furnishing_status"),
		"amenities": amenities,
		"gallery": gallery,
		"payment_plan_table": payment_plan,
		"project_units_table": project_units,
		"description": row.get("description"),
		"description_not_formatted": strip_html(row.get("description")) if row.get("description") else None,
		"handover_quarter": row.get("handover_quarter"),
		"handover_year": row.get("handover_year"),
	}


def serialize_property_detail(doc) -> dict[str, Any]:
	# AP-02: Guard against missing agent (e.g. off-plan properties or properties without an assigned agent)
	if not doc.agent:
		agent_doc = None
		link = None
		agency_details = None
		agent_payload = None
	else:
		agent_doc = frappe.get_doc("Agent", doc.agent)
		link = None
		whatsapp_number_for_links = _get_alora_whatsapp_number() or agent_doc.whatsapp_number or agent_doc.phone
		if whatsapp_number_for_links:
			number = str(whatsapp_number_for_links).replace("+", "").replace(" ", "")
			message = _("Hi, I am interested in {0}").format(doc.property_code or doc.name)
			link = f"https://wa.me/{number}?text={quote(message)}"

		agency_details = None
		agency_id = getattr(agent_doc, "agency", None)
		if agency_id:
			try:
				from . import agencies
				agency_details = agencies.get_agency_details(agency_id)
			except Exception:
				agency_details = None

	area_name = frappe.db.get_value("Area", doc.area, "area_name") if doc.area else None
	location = _build_location_label(area_name, doc.city, doc.state, doc.country)
	developer = _get_developer_profile(doc.developer)

	featured_until_value, featured_remaining = _get_featured_timer(doc.featured_until)
	completion_status = doc.completion_status
	completion_status_key = (completion_status or "").strip().lower()

	if agent_doc:
		agent_payload = {
			"id": agent_doc.name,
			"name": agent_doc.full_name or agent_doc.user,
			"phone": agent_doc.phone,
			"whatsapp_number": whatsapp_number_for_links,
			"whatsapp_link": _build_whatsapp_link(whatsapp_number_for_links),
			"email": agent_doc.email,
		}
		try:
			agent_payload["ratings"] = reviews.get_agent_rating_stats(doc.agent)
		except Exception:
			agent_payload["ratings"] = reviews.empty_agent_rating_summary()

	return {
		"id": doc.name,
		"title": doc.title,
		"listing_type": doc.listing_type,
		"completion_status": doc.completion_status,
		"property_type": doc.property_type,
		"property_category": doc.property_category,
		"status": doc.status,
		"price": doc.price,
		"currency": doc.currency,
		"bedrooms": doc.bedrooms,
		"bathrooms": doc.bathrooms,
		"area_sqft": doc.area_sqft,
		"city": doc.city,
		"location": location,
		"state": doc.state,
		"country": doc.country,
		"pincode": doc.pincode,
		"latitude": doc.latitude,
		"longitude": doc.longitude,
		"description": doc.description,
		"description_not_formatted": strip_html(doc.description) if doc.description else None,
		"area": doc.area,
		"area_name": area_name,
		"developer_id": developer["id"] if developer else None,
		"developer_name": developer["name"] if developer else None,
		"developer": developer,
		"furnishing_status": doc.furnishing_status,
		"primary_image_url": doc.primary_image,
		"is_featured": bool(doc.is_featured),
		"featured_until": featured_until_value,
		"featured_remaining_seconds": featured_remaining,
		"trakheesi_permit_number": doc.trakheesi_permit_number,
		"trakheesi_qr_code": doc.trakheesi_qr_code,
		"zone_name": doc.zone_name,
		"is_sold": bool(doc.is_sold),
		"is_rented": bool(doc.is_rented),
		"rent_type": doc.rent_type,
		"amenities": [
			frappe.db.get_value("Amenity", row.amenity_name, "amenity_name") or row.amenity_name
			for row in doc.amenities
		],
		"gallery": [
			{"image": row.image, "caption": row.caption, "sort_order": row.sort_order}
			for row in doc.gallery
		],
		"payment_plan_table": [
			{"payment_plan": r.payment_plan, "milestone": r.milestone, "percentage": r.percentage, "idx": r.idx}
			for r in getattr(doc, "payment_plan_table", [])
		],
		"project_units_table": _group_project_units(getattr(doc, "project_units_table", [])),
		"off_plan_agencies": _get_off_plan_agencies(doc.name),
		"agent": agent_payload,
		"agency": agency_details,
		"whatsapp_chat_link": link,
		"handover_quarter": doc.handover_quarter,
		"handover_year": doc.handover_year,
	}


def _validate_property_owner(doc):
	current_user = utils.get_current_user()
	if "System Manager" in frappe.get_roles(current_user):
		return

	agent_name = frappe.db.get_value("Agent", {"user": current_user}, "name")
	if not agent_name or doc.agent != agent_name:
		frappe.throw(_("You can only access properties you own."), frappe.PermissionError)


def _group_project_units(rows) -> list[dict]:
	"""AP-03: Group project unit rows into nested structure:
	[{property_type, units: [{num_bedrooms, layouts: [{layout_type, size, bathrooms, floor_plan}]}]}]
	"""
	from collections import OrderedDict

	# Use OrderedDict to preserve insertion order
	grouped: dict = OrderedDict()
	for r in rows:
		# Support both frappe doc objects and plain dicts
		pt = getattr(r, "property_type", None) or (r.get("property_type") if isinstance(r, dict) else None) or ""
		nb = getattr(r, "num_bedrooms", None) or (r.get("num_bedrooms") if isinstance(r, dict) else None)
		lt = getattr(r, "layout_type", None) or (r.get("layout_type") if isinstance(r, dict) else None)
		size = getattr(r, "size", None) or (r.get("size") if isinstance(r, dict) else None)
		baths = getattr(r, "bathrooms", None) or (r.get("bathrooms") if isinstance(r, dict) else None)
		fp = getattr(r, "floor_plan", None) or (r.get("floor_plan") if isinstance(r, dict) else None)

		if pt not in grouped:
			grouped[pt] = OrderedDict()
		nb_key = nb if nb is not None else ""
		if nb_key not in grouped[pt]:
			grouped[pt][nb_key] = []
		grouped[pt][nb_key].append({
			"layout_type": lt,
			"size": size,
			"bathrooms": baths,
			"floor_plan": fp,
		})

	result = []
	for property_type, bedrooms_map in grouped.items():
		units = []
		for num_bedrooms, layouts in bedrooms_map.items():
			units.append({"num_bedrooms": num_bedrooms, "layouts": layouts})
		result.append({"property_type": property_type, "units": units})
	return result


def _build_location_label(
	area_name: str | None,
	city: str | None,
	state: str | None,
	country: str | None,
) -> str | None:
	components: list[str] = []
	for value in (area_name, city, state, country):
		text = _clean_str(value)
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


def _get_developer_profile(developer_id: str | None) -> dict[str, Any] | None:
	if not developer_id:
		return None

	data = frappe.db.get_value(
		"Developer",
		developer_id,
		[
			"name",
			"developer_name",
			"status",
			"email",
			"phone",
			"website",
			"logo",
			"description",
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
		],
		as_dict=True,
	)
	if not data:
		return None

	location = _build_location_label(None, data.get("city"), data.get("state"), data.get("country"))
	return {
		"id": data.get("name"),
		"name": data.get("developer_name"),
		"status": data.get("status"),
		"email": data.get("email"),
		"phone": data.get("phone"),
		"website": data.get("website"),
		"logo": data.get("logo"),
		"description": data.get("description"),
		"description_not_formatted": strip_html(data.get("description")) if data.get("description") else None,
		"address_line1": data.get("address_line1"),
		"address_line2": data.get("address_line2"),
		"city": data.get("city"),
		"state": data.get("state"),
		"country": data.get("country"),
		"pincode": data.get("pincode"),
		"location": location,
	}


def _get_list_param(param: str) -> list[str]:
	raw_values: list[Any] = []
	getlist = getattr(frappe.form_dict, "getlist", None)
	if callable(getlist):
		raw_values = list(getlist(param) or [])
	if not raw_values:
		value = frappe.form_dict.get(param)
		if value is None:
			return []
		if isinstance(value, list):
			raw_values = value
		else:
			text = str(value).strip()
			if not text:
				return []
			try:
				parsed = json.loads(text)
			except (TypeError, ValueError):
				raw_values = [item.strip() for item in text.split(",") if item.strip()]
			else:
				if isinstance(parsed, list):
					raw_values = parsed
				else:
					raw_values = [parsed]

	values: list[str] = []
	for entry in raw_values:
		if isinstance(entry, (list, tuple)):
			for nested in entry:
				text = _clean_str(nested)
				if text:
					values.append(text)
		else:
			text = _clean_str(entry)
			if text:
				values.append(text)
	return values


def _get_float_param(param: str) -> float | None:
	value = frappe.form_dict.get(param)
	if value in (None, "", []):
		return None

	candidates = value if isinstance(value, (list, tuple)) else [value]
	for candidate in candidates:
		if candidate in (None, ""):
			continue
		try:
			return float(candidate)
		except (TypeError, ValueError):
			continue
	return None


def _get_int_param(param: str) -> int | None:
	value = frappe.form_dict.get(param)
	if value in (None, "", []):
		return None

	candidates = value if isinstance(value, (list, tuple)) else [value]
	for candidate in candidates:
		if candidate in (None, ""):
			continue
		try:
			return cint(candidate)
		except (TypeError, ValueError):
			continue
	return None


def _get_int_list_param(param: str) -> list[int]:
	values = []
	for entry in _get_list_param(param):
		try:
			values.append(cint(entry))
		except (TypeError, ValueError):
			continue
	return values


def _get_property_ids_with_all_amenities(amenities: list[str]) -> set[str]:
	names = {_find_existing_amenity(amenity) for amenity in amenities}
	names.discard(None)
	if not names:
		return set()

	property_ids: set[str] | None = None
	for amenity in names:
		matching = set(
			frappe.get_all(
				"Property Amenity",
				filters={"amenity_name": amenity},
				pluck="parent",
			)
		)
		if property_ids is None:
			property_ids = matching
		else:
			property_ids &= matching

		if not property_ids:
			return set()

	return property_ids or set()


def _clean_str(value: Any) -> str | None:
	if value is None:
		return None
	text = str(value).strip()
	return text or None


def _validate_title_letter_count(title: str) -> None:
	letter_count = len("".join(title.split()))
	if letter_count > TITLE_MAX_LETTERS:
		frappe.throw(
			_("Title must not exceed {0} letters.").format(TITLE_MAX_LETTERS),
			frappe.ValidationError,
		)


def _resolve_agent_scope() -> tuple[bool, str | None]:
	user = utils.get_current_user()
	if user == "Administrator":
		return False, None

	user_roles = set(frappe.get_roles(user))
	if "System Manager" in user_roles or "Agency Admin" in user_roles or "Agency Manager" in user_roles:
		return False, None

	if "Agent" in user_roles:
		agent_id = frappe.db.get_value("Agent", {"user": user}, "name")
		return True, agent_id

	return False, None


def resolve_agent_scope() -> tuple[bool, str | None]:
	return _resolve_agent_scope()


def _enforce_agent_property_scope(doc):
	restrict, agent_id = _resolve_agent_scope()
	if not restrict:
		return

	if not agent_id:
		frappe.throw(_("Agent profile not found."), frappe.PermissionError)

	if doc.agent != agent_id:
		frappe.throw(_("You can only access properties you own."), frappe.PermissionError)


def _ensure_amenity_master(value: Any) -> str | None:
	name = _clean_str(value)
	if not name:
		return None

	docname = frappe.db.exists("Amenity", {"name": name}) or frappe.db.exists(
		"Amenity", {"amenity_name": name}
	)
	if docname:
		return docname

	doc = frappe.get_doc({"doctype": "Amenity", "amenity_name": name})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _get_off_plan_agencies(property_id: str) -> list[dict[str, Any]]:
	if not property_id:
		return []
	rows = frappe.get_all(
		"Property Agency",
		filters={"parent": property_id},
		fields=["agency"],
	)
	agencies_list = []
	if not rows:
		return agencies_list
	try:
		from . import agencies
	except Exception:
		return agencies_list
	for row in rows:
		agency_id = row.get("agency")
		agency_details = agencies.get_agency_details(agency_id)
		if agency_details:
			agencies_list.append(agency_details)
		else:
			if agency_id:
				agencies_list.append({"id": agency_id})
	return agencies_list


def _build_whatsapp_link(number: str | None) -> str | None:
	if not number:
		return None
	clean_number = str(number).replace("+", "").replace(" ", "")
	return f"https://wa.me/{clean_number}" if clean_number else None


def _get_alora_whatsapp_number() -> str | None:
	number = frappe.db.get_single_value("FCRM Settings", "alora_whatsapp_number")
	if not number:
		return None
	clean = str(number).strip()
	return clean or None


def _normalize_featured_until(value: Any, is_featured: int) -> datetime | None:
	if not value:
		return None if not is_featured else _validate_featured_required(value)
	try:
		featured_until = get_datetime(value)
	except Exception:
		frappe.throw(_("Invalid featured_until datetime."), frappe.ValidationError)

	if is_featured and featured_until <= now_datetime():
		frappe.throw(_("featured_until must be in the future for featured properties."), frappe.ValidationError)
	return featured_until


def _validate_featured_required(value: Any) -> None:
	frappe.throw(_("featured_until is required when is_featured is enabled."), frappe.ValidationError)


def _get_featured_timer(featured_until: Any) -> tuple[str | None, int]:
	if not featured_until:
		return None, 0
	featured_dt = get_datetime(featured_until)
	remaining = int((featured_dt - now_datetime()).total_seconds())
	return str(featured_dt), max(0, remaining)


def expire_featured_properties():
	"""Scheduled job to auto-expire featured properties."""
	now = now_datetime()
	has_featured_from_column = frappe.db.has_column("Property", "featured_from")
	expired_fields = ["name", "agent", "featured_until"]
	if has_featured_from_column:
		expired_fields.append("featured_from")
	expired = frappe.db.get_all(
		"Property",
		filters={"is_featured": 1, "featured_until": ["<", now]},
		fields=expired_fields,
	)
	if not expired:
		return {"expired_count": 0}

	for row in expired:
		featured_logs.create_property_featured_log(
			row["name"],
			agent=row.get("agent"),
			event_type="Expired",
			source="Scheduler",
			featured_from=row.get("featured_from"),
			featured_until=row.get("featured_until"),
			notes="Featured window expired by scheduler.",
		)

	frappe.db.sql(
		"""
		UPDATE `tabProperty`
		SET is_featured = 0, featured_until = NULL {featured_from_clause}
		WHERE name IN %(names)s
		""".format(
			featured_from_clause=", featured_from = NULL" if has_featured_from_column else ""
		),
		{"names": tuple(row["name"] for row in expired)},
	)
	frappe.db.commit()
	return {"expired_count": len(expired)}


def _find_existing_amenity(value: Any) -> str | None:
	name = _clean_str(value)
	if not name:
		return None
	return frappe.db.exists("Amenity", {"name": name}) or frappe.db.exists(
		"Amenity", {"amenity_name": name}
	)


def validate_featured_purchase_properties(
	property_ids: list[str],
	*,
	agency_name: str,
	featured_from: Any,
	featured_until: Any,
) -> list[dict[str, Any]]:
	"""Validate selected properties for paid featured activation."""
	if not property_ids:
		frappe.throw(_("Please select at least one property."))
	if not agency_name:
		frappe.throw(_("Agency is required for featured purchase validation."))

	try:
		featured_from_dt = get_datetime(featured_from)
		featured_until_dt = get_datetime(featured_until)
	except Exception:
		frappe.throw(_("Invalid featured date range."), frappe.ValidationError)

	if featured_until_dt <= featured_from_dt:
		frappe.throw(_("Featured end date must be after start date."), frappe.ValidationError)

	normalized_ids = [str(p).strip() for p in property_ids if str(p).strip()]
	unique_ids = list(dict.fromkeys(normalized_ids))
	rows = frappe.get_all(
		"Property",
		filters={"name": ["in", unique_ids]},
		fields=["name", "title", "agency", "status", "is_featured", "featured_from", "featured_until"],
	)
	rows_by_name = {row["name"]: row for row in rows}

	missing = [name for name in unique_ids if name not in rows_by_name]
	if missing:
		frappe.throw(_("Some selected properties were not found: {0}").format(", ".join(missing)))

	for name in unique_ids:
		row = rows_by_name[name]
		if (row.get("agency") or "") != agency_name:
			frappe.throw(_("Property {0} does not belong to your agency.").format(name), frappe.PermissionError)
		if (row.get("status") or "") != "Active":
			frappe.throw(_("Only Active properties can be featured. Property: {0}").format(name), frappe.ValidationError)
		if cint(row.get("is_featured")) and row.get("featured_until"):
			current_until = get_datetime(row.get("featured_until"))
			if current_until >= featured_from_dt:
				frappe.throw(
					_("Property {0} already has an overlapping featured period.").format(name),
					frappe.ValidationError,
				)

	return [rows_by_name[name] for name in unique_ids]


def activate_featured_properties(
	property_ids: list[str],
	*,
	agency_name: str,
	featured_from: Any,
	featured_until: Any,
	source: str = "Billing",
) -> list[dict[str, Any]]:
	"""Activate featured dates after successful payment."""
	valid_rows = validate_featured_purchase_properties(
		property_ids,
		agency_name=agency_name,
		featured_from=featured_from,
		featured_until=featured_until,
	)
	featured_from_dt = get_datetime(featured_from)
	featured_until_dt = get_datetime(featured_until)
	has_featured_from_column = frappe.db.has_column("Property", "featured_from")

	for row in valid_rows:
		update_values = {
			"is_featured": 1,
			"featured_until": featured_until_dt,
		}
		if has_featured_from_column:
			update_values["featured_from"] = featured_from_dt

		frappe.db.set_value(
			"Property",
			row["name"],
			update_values,
		)
		featured_logs.create_property_featured_log(
			row["name"],
			agent=frappe.db.get_value("Property", row["name"], "agent"),
			event_type="Activated",
			source=source,
			featured_from=featured_from_dt,
			featured_until=featured_until_dt,
			notes="Featured window activated after successful payment.",
		)

	return [
		{
			"property_id": row["name"],
			"title": row.get("title"),
			"featured_from": str(featured_from_dt),
			"featured_until": str(featured_until_dt),
			"featured_days": (getdate(featured_until_dt) - getdate(featured_from_dt)).days + 1,
		}
		for row in valid_rows
	]




