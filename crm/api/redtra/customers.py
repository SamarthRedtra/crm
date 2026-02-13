from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.query_builder import DocType, Order, functions as fn
from frappe.utils import cint

from . import utils, favorites, appointments


@frappe.whitelist()
@utils.require_jwt()
def list_customers() -> dict[str, Any]:
	page = max(1, cint(frappe.form_dict.get("page") or 1))
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page_size = max(1, min(page_size, 100))
	offset = (page - 1) * page_size

	search_term = frappe.form_dict.get("search")

	Customer = DocType("Customer")
	query = (
		frappe.qb.from_(Customer)
		.select(
			Customer.name.as_("id"),
			Customer.full_name,
			Customer.email,
			Customer.phone,
			Customer.whatsapp_number,
			Customer.preferred_city,
			Customer.user,
			Customer.creation.as_("created_at"),
			Customer.modified.as_("updated_at"),
		)
		.orderby(Customer.creation, order=Order.desc)
		.offset(offset)
		.limit(page_size)
	)

	if search_term:
		query = query.where(
			(Customer.full_name.like(f"%{search_term}%"))
			| (Customer.email.like(f"%{search_term}%"))
			| (Customer.phone.like(f"%{search_term}%"))
		)

	customers = []
	for row in query.run(as_dict=True):
		customers.append(_serialize_customer(row))

	# Get total count
	count_query = frappe.qb.from_(Customer).select(fn.Count(Customer.name))
	if search_term:
		count_query = count_query.where(
			(Customer.full_name.like(f"%{search_term}%"))
			| (Customer.email.like(f"%{search_term}%"))
			| (Customer.phone.like(f"%{search_term}%"))
		)
	
	total_count = int(count_query.run()[0][0] or 0)

	return {
		"items": customers,
		"page": page,
		"page_size": page_size,
		"total_items": total_count,
		"total_pages": (total_count + page_size - 1) // page_size if page_size else 0,
	}


@frappe.whitelist()
@utils.require_jwt()
def get_customer(customer_id: str) -> dict[str, Any]:
	if not frappe.db.exists("Customer", customer_id):
		frappe.throw(_("Customer not found"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Customer", customer_id)
	return _serialize_customer(doc, detail=True)


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def create_customer() -> dict[str, Any]:
	data = utils.get_request_json()
	
	# Basic validation
	required_fields = ["full_name", "email"]
	for field in required_fields:
		if not data.get(field):
			frappe.throw(_("Missing required field: {0}").format(field))

	# Check if user exists for email, if not create one? 
	# For now, let's assume we link to an existing user or create a new user if needed.
	# The Customer doctype has a mandatory 'user' link field.
	# If we are creating a customer via API, we might need to create a User first or find one.
	
	email = data.get("email")
	user_name = frappe.db.get_value("User", {"email": email}, "name")
	
	if not user_name:
		# Create a new user if not exists
		user_doc = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": data.get("full_name"),
			"send_welcome_email": 0,
			"enabled": 1
		})
		user_doc.insert(ignore_permissions=True)
		user_name = user_doc.name

	# Ensure user has Customer role
	if "Customer" not in frappe.get_roles(user_name):
		user_doc = frappe.get_doc("User", user_name)
		user_doc.add_roles("Customer")

	# Check if customer already exists for this user
	if frappe.db.exists("Customer", {"user": user_name}):
		frappe.throw(_("Customer already exists for this user"))

	doc = frappe.get_doc({
		"doctype": "Customer",
		"user": user_name,
		"full_name": data.get("full_name"),
		"email": email,
		"phone": data.get("phone"),
		"whatsapp_number": data.get("whatsapp_number"),
		"preferred_city": data.get("preferred_city")
	})
	
	doc.insert()
	return _serialize_customer(doc, detail=True)


@frappe.whitelist(methods=["PUT"])
@utils.require_jwt()
def update_customer(customer_id: str) -> dict[str, Any]:
	if not frappe.db.exists("Customer", customer_id):
		frappe.throw(_("Customer not found"), frappe.DoesNotExistError)

	data = utils.get_request_json()
	doc = frappe.get_doc("Customer", customer_id)

	editable_fields = ["full_name", "phone", "whatsapp_number", "preferred_city"]
	for field in editable_fields:
		if field in data:
			doc.set(field, data[field])

	doc.save()
	return _serialize_customer(doc, detail=True)


@frappe.whitelist(methods=["DELETE"])
@utils.require_jwt()
def delete_customer(customer_id: str) -> dict[str, Any]:
	if not frappe.db.exists("Customer", customer_id):
		frappe.throw(_("Customer not found"), frappe.DoesNotExistError)

	frappe.delete_doc("Customer", customer_id, ignore_permissions=True)
	return {"message": "Customer deleted successfully"}


def _serialize_customer(row: Any, detail: bool = False) -> dict[str, Any]:
	# row can be a dict (from query) or a Document object
	data = {}
	if isinstance(row, dict):
		data = {
			"id": row.get("id"),
			"full_name": row.get("full_name"),
			"email": row.get("email"),
			"phone": row.get("phone"),
			"whatsapp_number": row.get("whatsapp_number"),
			"preferred_city": row.get("preferred_city"),
			"user_id": row.get("user"),
			"created_at": row.get("created_at"),
		}
	else:
		data = {
			"id": row.name,
			"full_name": row.full_name,
			"email": row.email,
			"phone": row.phone,
			"whatsapp_number": row.whatsapp_number,
			"preferred_city": row.preferred_city,
			"user_id": row.user,
			"created_at": row.creation,
		}

	if detail:
		user_id = data.get("user_id")
		customer_id = data.get("id")

		# Fetch favorites
		if user_id:
			data["favorites"] = favorites.get_favorites_by_user(user_id)
		else:
			data["favorites"] = []

		# Fetch appointments
		if customer_id:
			data["appointments"] = appointments.get_customer_appointments(customer_id)
		else:
			data["appointments"] = []

	return data
