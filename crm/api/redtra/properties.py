from __future__ import annotations

from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint

from . import utils

SUMMARY_FIELDS = [
	"name",
	"title",
	"listing_type",
	"property_type",
	"price",
	"currency",
	"bedrooms",
	"bathrooms",
	"area_sqft",
	"city",
	"area",
	"primary_image",
	"status",
]


@frappe.whitelist()
@utils.require_jwt()
def list_properties() -> dict[str, Any]:
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	listing_type = frappe.form_dict.get("listing_type")
	min_price = frappe.form_dict.get("min_price")
	max_price = frappe.form_dict.get("max_price")
	bedrooms = frappe.form_dict.get("bedrooms")
	area = frappe.form_dict.get("area")
	city = frappe.form_dict.get("city")
	agent = frappe.form_dict.get("agent")

	filters: list[list[Any]] = [["Property", "status", "=", "Active"]]

	if listing_type:
		filters.append(["Property", "listing_type", "=", listing_type])
	if min_price:
		filters.append(["Property", "price", ">=", float(min_price)])
	if max_price:
		filters.append(["Property", "price", "<=", float(max_price)])
	if bedrooms:
		filters.append(["Property", "bedrooms", "=", cint(bedrooms)])
	if area:
		filters.append(["Property", "area", "=", area])
	if city:
		filters.append(["Property", "city", "=", city])
	if agent:
		filters.append(["Property", "agent", "=", agent])

	result = utils.get_paginated_list(
		"Property",
		filters=filters,
		fields=SUMMARY_FIELDS,
		page=page,
		page_size=page_size,
		order_by="modified desc",
	)
	result["items"] = [serialize_property_summary(row) for row in result["items"]]
	return result


@frappe.whitelist()
@utils.require_jwt()
def get_property(property_id: str) -> dict[str, Any]:
	doc = frappe.get_doc("Property", property_id)
	doc.check_permission("read")
	if doc.status != "Active":
		frappe.throw(_("Property is not active."), frappe.PermissionError)
	return serialize_property_detail(doc)


@frappe.whitelist()
@utils.require_jwt(roles={"Agent", "System Manager"})
def create_property() -> dict[str, Any]:
	data = utils.get_request_json(["title", "listing_type", "property_type", "price", "currency"])
	current_user = utils.get_current_user()
	agent_name = data.get("agent") or frappe.db.get_value("Agent", {"user": current_user}, "name")
	if not agent_name:
		frappe.throw(_("You must be a verified agent to create properties."), frappe.PermissionError)

	doc = frappe.get_doc(
		{
			"doctype": "Property",
			"title": data["title"],
			"listing_type": data["listing_type"],
			"property_type": data["property_type"],
			"price": data["price"],
			"currency": data["currency"],
			"bedrooms": data.get("bedrooms"),
			"bathrooms": data.get("bathrooms"),
			"area_sqft": data.get("area_sqft"),
			"area": data.get("area_id"),
			"address_line1": data.get("address_line1"),
			"address_line2": data.get("address_line2"),
			"city": data.get("city"),
			"state": data.get("state"),
			"country": data.get("country"),
			"pincode": data.get("pincode"),
			"latitude": data.get("latitude"),
			"longitude": data.get("longitude"),
			"description": data.get("description"),
			"agent": agent_name,
			"primary_image": data.get("primary_image"),
			"is_featured": data.get("is_featured") or 0,
		}
	)

	for amenity in data.get("amenities") or []:
		if isinstance(amenity, dict):
			value = amenity.get("amenity_name")
		else:
			value = amenity
		if value:
			doc.append("amenities", {"amenity_name": value})

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

	doc.update(
		{
			"title": data.get("title") or doc.title,
			"listing_type": data.get("listing_type") or doc.listing_type,
			"property_type": data.get("property_type") or doc.property_type,
			"price": data.get("price", doc.price),
			"currency": data.get("currency") or doc.currency,
			"bedrooms": data.get("bedrooms", doc.bedrooms),
			"bathrooms": data.get("bathrooms", doc.bathrooms),
			"area_sqft": data.get("area_sqft", doc.area_sqft),
			"area": data.get("area_id", doc.area),
			"address_line1": data.get("address_line1", doc.address_line1),
			"address_line2": data.get("address_line2", doc.address_line2),
			"city": data.get("city", doc.city),
			"state": data.get("state", doc.state),
			"country": data.get("country", doc.country),
			"pincode": data.get("pincode", doc.pincode),
			"latitude": data.get("latitude", doc.latitude),
			"longitude": data.get("longitude", doc.longitude),
			"description": data.get("description", doc.description),
			"is_featured": data.get("is_featured", doc.is_featured),
			"status": data.get("status", doc.status),
		}
	)

	if "amenities" in data:
		doc.set("amenities", [])
		for amenity in data.get("amenities") or []:
			value = amenity.get("amenity_name") if isinstance(amenity, dict) else amenity
			if value:
				doc.append("amenities", {"amenity_name": value})

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
	number = agent.whatsapp_number or agent.phone
	if not number:
		frappe.throw(_("Agent does not have a WhatsApp number configured."))

	message = _("Hi, I am interested in {0}").format(doc.property_code or doc.name)
	link = f"https://wa.me/{number.replace('+', '').replace(' ', '')}?text={quote(message)}"
	return {"whatsapp_chat_link": link}


def serialize_property_summary(row: dict[str, Any]) -> dict[str, Any]:
	area_name = None
	if row.get("area"):
		area_name = frappe.db.get_value("Area", row["area"], "area_name")

	return {
		"id": row.get("name"),
		"title": row.get("title"),
		"listing_type": row.get("listing_type"),
		"property_type": row.get("property_type"),
		"price": row.get("price"),
		"currency": row.get("currency"),
		"bedrooms": row.get("bedrooms"),
		"bathrooms": row.get("bathrooms"),
		"area_sqft": row.get("area_sqft"),
		"city": row.get("city"),
		"area": row.get("area"),
		"area_name": area_name,
		"primary_image_url": row.get("primary_image"),
	}


def serialize_property_detail(doc) -> dict[str, Any]:
	agent_doc = frappe.get_doc("Agent", doc.agent)
	area_name = frappe.db.get_value("Area", doc.area, "area_name") if doc.area else None

	link = None
	if agent_doc.whatsapp_number or agent_doc.phone:
		number = (agent_doc.whatsapp_number or agent_doc.phone).replace("+", "").replace(" ", "")
		message = _("Hi, I am interested in {0}").format(doc.property_code or doc.name)
		link = f"https://wa.me/{number}?text={quote(message)}"

	return {
		"id": doc.name,
		"title": doc.title,
		"listing_type": doc.listing_type,
		"property_type": doc.property_type,
		"status": doc.status,
		"price": doc.price,
		"currency": doc.currency,
		"bedrooms": doc.bedrooms,
		"bathrooms": doc.bathrooms,
		"area_sqft": doc.area_sqft,
		"city": doc.city,
		"state": doc.state,
		"country": doc.country,
		"pincode": doc.pincode,
		"latitude": doc.latitude,
		"longitude": doc.longitude,
		"description": doc.description,
		"area": doc.area,
		"area_name": area_name,
		"primary_image_url": doc.primary_image,
		"amenities": [row.amenity_name for row in doc.amenities],
		"gallery": [
			{"image": row.image, "caption": row.caption, "sort_order": row.sort_order}
			for row in doc.gallery
		],
		"agent": {
			"id": agent_doc.name,
			"name": agent_doc.full_name or agent_doc.user,
			"phone": agent_doc.phone,
			"whatsapp_number": agent_doc.whatsapp_number,
		},
		"whatsapp_chat_link": link,
	}


def _validate_property_owner(doc):
	current_user = utils.get_current_user()
	if "System Manager" in frappe.get_roles(current_user):
		return

	agent_name = frappe.db.get_value("Agent", {"user": current_user}, "name")
	if not agent_name or doc.agent != agent_name:
		frappe.throw(_("You can only access properties you own."), frappe.PermissionError)

