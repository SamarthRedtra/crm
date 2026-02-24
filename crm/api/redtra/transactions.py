from __future__ import annotations

import math
from typing import Any

import frappe
from frappe import _
from frappe.query_builder import DocType, Order, functions as fn
from frappe.utils import cint, today

from . import utils


@frappe.whitelist(allow_guest=True)
def list_transactions() -> dict[str, Any]:
	"""List transactions for the authenticated agent (or all for System Manager/Guest)."""
	with utils.maybe_authenticate_jwt():
		current_user = utils.get_current_user()
		is_system_manager = current_user and "System Manager" in frappe.get_roles(current_user)

		page = max(1, cint(frappe.form_dict.get("page") or 1))
		page_size = cint(frappe.form_dict.get("page_size") or 20)
		page_size = max(1, min(page_size, 100))
		offset = (page - 1) * page_size

		TXN = DocType("Property Transaction Log")
		PROP = DocType("Property")

		filters = []

		# Scope to the agent unless System Manager or Guest
		if current_user and not is_system_manager:
			agent_name = frappe.db.get_value("Agent", {"user": current_user}, "name")
			if not agent_name:
				return {
					"items": [],
					"page": page,
					"page_size": page_size,
					"total_items": 0,
					"total_pages": 0,
				}
			filters.append(TXN.agent == agent_name)
		elif is_system_manager:
			# Optional agent filter for System Manager
			agent_filter = (frappe.form_dict.get("agent") or "").strip()
			if agent_filter:
				filters.append(TXN.agent == agent_filter)

		# Optional filters
		property_filter = (frappe.form_dict.get("property") or "").strip()
		if property_filter:
			filters.append(TXN.property == property_filter)

		customer_filter = (frappe.form_dict.get("customer") or "").strip()
		if customer_filter:
			filters.append(TXN.customer == customer_filter)

		transaction_type = (frappe.form_dict.get("transaction_type") or "").strip()
		if transaction_type:
			filters.append(TXN.transaction_type == transaction_type)

		# NEW: Off Plan Filter
		off_plan = frappe.form_dict.get("off_plan")
		if off_plan is not None:
			is_off_plan = utils._coerce_bool(off_plan) if hasattr(utils, "_coerce_bool") else str(off_plan).lower() in ("1", "true", "yes")
			if is_off_plan:
				filters.append(PROP.completion_status == "Off-plan")
			else:
				filters.append(PROP.completion_status != "Off-plan")

		# NEW: Property Type Filter
		property_types = frappe.form_dict.get("property_types") or frappe.form_dict.get("property_type")
		if property_types:
			if isinstance(property_types, str):
				property_types = property_types.split(",")
			filters.append(PROP.property_type.isin(property_types))

		# Price Range
		min_price = frappe.form_dict.get("min_price")
		if min_price:
			filters.append(TXN.amount >= float(min_price))
		max_price = frappe.form_dict.get("max_price")
		if max_price:
			filters.append(TXN.amount <= float(max_price))

		# Area Range
		min_area = frappe.form_dict.get("min_area") or frappe.form_dict.get("min_area_sqft")
		if min_area:
			filters.append(PROP.area_sqft >= float(min_area))
		max_area = frappe.form_dict.get("max_area") or frappe.form_dict.get("max_area_sqft")
		if max_area:
			filters.append(PROP.area_sqft <= float(max_area))

		# Date Range
		from_date = (frappe.form_dict.get("from_date") or "").strip()
		if from_date:
			filters.append(TXN.transaction_date >= from_date)

		to_date = (frappe.form_dict.get("to_date") or "").strip()
		if to_date:
			filters.append(TXN.transaction_date <= to_date)

		# Location Search
		location = (frappe.form_dict.get("location") or "").strip()
		if location:
			loc_like = f"%{location}%"
			filters.append(
				(PROP.area.like(loc_like)) | 
				(PROP.city.like(loc_like)) | 
				(PROP.state.like(loc_like)) | 
				(PROP.title.like(loc_like))
			)

		query = (
			frappe.qb.from_(TXN)
			.inner_join(PROP).on(TXN.property == PROP.name)
			.select(
				TXN.name.as_("id"),
				TXN.property,
				TXN.agent,
				TXN.customer,
				TXN.transaction_date,
				TXN.transaction_type,
				TXN.amount,
				TXN.currency,
				TXN.notes,
				TXN.creation.as_("created_at"),
				TXN.modified.as_("updated_at"),
				PROP.title.as_("property_title"),
				PROP.primary_image.as_("property_image"),
				PROP.area_sqft,
				PROP.property_type,
				PROP.area.as_("location_area"),
				PROP.city.as_("location_city"),
			)
			.orderby(TXN.transaction_date, order=Order.desc)
			.offset(offset)
			.limit(page_size)
		)

		count_query = (
			frappe.qb.from_(TXN)
			.inner_join(PROP).on(TXN.property == PROP.name)
			.select(fn.Count(TXN.name))
		)

		for f in filters:
			query = query.where(f)
			count_query = count_query.where(f)

		rows = query.run(as_dict=True)
		items = [_serialize_transaction(row) for row in rows]

		total_items = int(count_query.run()[0][0] or 0)
		total_pages = math.ceil(total_items / page_size) if page_size else 0

		return {
			"items": items,
			"page": page,
			"page_size": page_size,
			"total_items": total_items,
			"total_pages": total_pages,
		}


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def create_transaction() -> dict[str, Any]:
	"""Create a new property transaction log."""
	data = utils.get_request_json(["property", "transaction_type"])
	current_user = utils.get_current_user()

	agent_name = data.get("agent") or frappe.db.get_value("Agent", {"user": current_user}, "name")
	if not agent_name:
		frappe.throw(_("You must be associated with an agent to create transactions."), frappe.PermissionError)

	# Validate property exists
	if not frappe.db.exists("Property", data["property"]):
		frappe.throw(_("Property not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc(
		{
			"doctype": "Property Transaction Log",
			"property": data["property"],
			"agent": agent_name,
			"customer": data.get("customer"),
			"transaction_date": data.get("transaction_date") or today(),
			"transaction_type": data["transaction_type"],
			"amount": data.get("amount"),
			"currency": data.get("currency"),
			"notes": data.get("notes"),
		}
	)
	doc.insert(ignore_permissions=True)

	# If transaction type is Sale, mark property as sold
	if data["transaction_type"] == "Sale":
		frappe.db.set_value("Property", data["property"], "is_sold", 1)

	frappe.response.http_status_code = 201
	return _serialize_transaction(doc, detail=True)


@frappe.whitelist()
@utils.require_jwt()
def get_transaction(transaction_id: str) -> dict[str, Any]:
	"""Get a single transaction log."""
	if not frappe.db.exists("Property Transaction Log", transaction_id):
		frappe.throw(_("Transaction not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Property Transaction Log", transaction_id)
	return _serialize_transaction(doc, detail=True)


def _serialize_transaction(row: Any, detail: bool = False) -> dict[str, Any]:
	if isinstance(row, dict):
		result = {
			"id": row.get("id") or row.get("name"),
			"property": row.get("property"),
			"agent": row.get("agent"),
			"customer": row.get("customer"),
			"transaction_date": str(row.get("transaction_date")) if row.get("transaction_date") else None,
			"transaction_type": row.get("transaction_type"),
			"amount": row.get("amount"),
			"currency": row.get("currency"),
			"notes": row.get("notes"),
			"created_at": str(row.get("created_at")) if row.get("created_at") else None,
			# From Join
			"property_title": row.get("property_title"),
			"property_image": row.get("property_image"),
			"area_sqft": row.get("area_sqft"),
			"property_type": row.get("property_type"),
			"location_area": row.get("location_area"),
			"location_city": row.get("location_city"),
		}
	else:
		result = {
			"id": row.name,
			"property": row.property,
			"agent": row.agent,
			"customer": row.customer,
			"transaction_date": str(row.transaction_date) if row.transaction_date else None,
			"transaction_type": row.transaction_type,
			"amount": row.amount,
			"currency": row.currency,
			"notes": row.notes,
			"created_at": str(row.creation) if row.creation else None,
		}
		# Fetch property info if missing (for Document objects or non-join rows)
		prop_info = frappe.db.get_value(
			"Property", 
			result["property"], 
			["title", "primary_image", "area_sqft", "property_type", "area", "city"], 
			as_dict=True
		) if result["property"] else {}
		if prop_info:
			result.update({
				"property_title": prop_info.get("title"),
				"property_image": prop_info.get("primary_image"),
				"area_sqft": prop_info.get("area_sqft"),
				"property_type": prop_info.get("property_type"),
				"location_area": prop_info.get("area"),
				"location_city": prop_info.get("city"),
			})

	# Enriched Metrics
	result["formatted_amount"] = utils.format_amount_compact(result["amount"])
	
	if result.get("amount") and result.get("area_sqft"):
		price_per_sqft = float(result["amount"]) / float(result["area_sqft"])
		result["price_per_sqft"] = round(price_per_sqft, 2)
		result["formatted_price_per_sqft"] = utils.format_amount_compact(price_per_sqft)

	if detail:
		# Add extra details for single object view
		agent_name = frappe.db.get_value("Agent", result["agent"], "full_name") if result["agent"] else None
		customer_name = frappe.db.get_value("Customer", result["customer"], "full_name") if result.get("customer") else None
		result["agent_name"] = agent_name
		result["customer_name"] = customer_name

	return result
