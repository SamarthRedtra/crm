from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime

from . import properties, utils


@frappe.whitelist()
@utils.require_jwt()
def list_appointments() -> list[dict[str, Any]]:
	user = utils.get_current_user()
	roles = set(frappe.get_roles(user))

	filters: dict[str, Any] = {}
	if "Agent" in roles:
		agent_name = frappe.db.get_value("Agent", {"user": user})
		if agent_name:
			filters["agent"] = agent_name
	if not filters:
		customer = utils.get_customer_by_user(user)
		if not customer:
			return []
		filters["customer"] = customer.name

	records = frappe.get_all(
		"Property Appointment",
		filters=filters,
		fields=[
			"name",
			"customer",
			"agent",
			"property",
			"start_datetime",
			"end_datetime",
			"status",
			"notes",
			"source",
		],
		order_by="start_datetime desc",
	)

	return [serialize_appointment(record["name"]) for record in records]


@frappe.whitelist()
@utils.require_jwt()
def create_appointment() -> dict[str, Any]:
	data = utils.get_request_json(["property_id", "start_datetime", "end_datetime"])
	property_id = data["property_id"]

	prop = frappe.get_doc("Property", property_id)
	if prop.status != "Active":
		frappe.throw(_("Only active properties can be booked."))

	agent_name = prop.agent
	if not agent_name:
		frappe.throw(_("Property {0} is not assigned to an agent.").format(prop.name))

	customer = utils.get_customer_by_user(utils.get_current_user())
	if not customer:
		frappe.throw(_("Customer profile is required to book an appointment."))

	start_datetime = get_datetime(data["start_datetime"])
	end_datetime = get_datetime(data["end_datetime"])

	doc = frappe.get_doc(
		{
			"doctype": "Property Appointment",
			"customer": customer.name,
			"agent": agent_name,
			"property": property_id,
			"start_datetime": start_datetime,
			"end_datetime": end_datetime,
			"notes": data.get("notes"),
			"source": "Mobile App",
		}
	)
	doc.insert(ignore_permissions=True)

	event_name = _create_calendar_event(doc, prop, customer)
	if event_name:
		doc.db_set("calendar_event", event_name, update_modified=False)

	frappe.response.http_status_code = 201
	return serialize_appointment(doc.name)


@frappe.whitelist()
@utils.require_jwt()
def get_appointment(appointment_id: str) -> dict[str, Any]:
	_ensure_appointment_access(appointment_id)
	return serialize_appointment(appointment_id)


@frappe.whitelist()
@utils.require_jwt()
def update_appointment(appointment_id: str) -> dict[str, Any]:
	doc = _ensure_appointment_access(appointment_id)
	if doc.status != "Scheduled":
		frappe.throw(_("Only scheduled appointments can be updated."))

	data = utils.get_request_json()
	if data.get("start_datetime"):
		doc.start_datetime = get_datetime(data["start_datetime"])
	if data.get("end_datetime"):
		doc.end_datetime = get_datetime(data["end_datetime"])
	if data.get("notes") is not None:
		doc.notes = data["notes"]

	doc.save(ignore_permissions=True)
	_update_calendar_event(doc)
	return serialize_appointment(doc.name)


@frappe.whitelist()
@utils.require_jwt()
def cancel_appointment(appointment_id: str) -> dict[str, Any]:
	doc = _ensure_appointment_access(appointment_id)
	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	_update_calendar_event(doc)
	frappe.response.http_status_code = 204
	return {}


def serialize_appointment(name: str) -> dict[str, Any]:
	doc = frappe.get_doc("Property Appointment", name)
	customer = frappe.get_doc("Customer", doc.customer)
	property_doc = frappe.get_doc("Property", doc.property)
	property_summary = properties.serialize_property_summary(
		{field: getattr(property_doc, field, None) for field in properties.SUMMARY_FIELDS}
	)
	agent_doc = frappe.get_doc("Agent", doc.agent) if doc.agent else None

	return {
		"id": doc.name,
		"status": doc.status,
		"start_datetime": doc.start_datetime,
		"end_datetime": doc.end_datetime,
		"notes": doc.notes,
		"source": doc.source,
		"customer": {
			"id": customer.name,
			"name": customer.full_name,
			"phone": customer.phone,
			"email": customer.email,
		},
		"agent": {
			"id": agent_doc.name if agent_doc else None,
			"name": agent_doc.full_name if agent_doc else None,
			"phone": agent_doc.phone if agent_doc else None,
			"whatsapp_number": agent_doc.whatsapp_number if agent_doc else None,
		},
		"property": property_summary,
		"calendar_event": doc.calendar_event,
	}


def _ensure_appointment_access(appointment_id: str):
	doc = frappe.get_doc("Property Appointment", appointment_id)
	user = utils.get_current_user()
	roles = set(frappe.get_roles(user))

	if "System Manager" in roles:
		return doc

	if "Agent" in roles:
		agent_name = frappe.db.get_value("Agent", {"user": user})
		if agent_name and doc.agent == agent_name:
			return doc

	customer = utils.get_customer_by_user(user)
	if customer and doc.customer == customer.name:
		return doc

	frappe.throw(_("You do not have access to this appointment."), frappe.PermissionError)


def _create_calendar_event(appointment_doc, property_doc, customer_doc):
	subject = _("Property Viewing: {0}").format(property_doc.title or property_doc.name)
	description = _build_event_description(appointment_doc, property_doc, customer_doc)

	event_doc = frappe.get_doc(
		{
			"doctype": "Event",
			"subject": subject,
			"event_category": "Meeting",
			"event_type": "Private",
			"starts_on": appointment_doc.start_datetime,
			"ends_on": appointment_doc.end_datetime,
			"status": "Open",
			"reference_doctype": "Property",
			"reference_docname": property_doc.name,
			"description": description,
		}
	)

	agent_user = frappe.db.get_value("Agent", appointment_doc.agent, "user")
	if agent_user:
		event_doc.append(
			"event_participants",
			{"reference_doctype": "User", "reference_docname": agent_user},
		)

	customer_user = getattr(customer_doc, "user", None)
	if customer_user:
		event_doc.append(
			"event_participants",
			{"reference_doctype": "User", "reference_docname": customer_user},
		)

	event_doc.insert(ignore_permissions=True)
	return event_doc.name


def _update_calendar_event(appointment_doc):
	if not appointment_doc.calendar_event:
		return

	try:
		event_doc = frappe.get_doc("Event", appointment_doc.calendar_event)
	except frappe.DoesNotExistError:
		return

	property_doc = frappe.get_doc("Property", appointment_doc.property)
	customer_doc = frappe.get_doc("Customer", appointment_doc.customer)

	event_doc.starts_on = appointment_doc.start_datetime
	event_doc.ends_on = appointment_doc.end_datetime
	event_doc.description = _build_event_description(appointment_doc, property_doc, customer_doc)

	if appointment_doc.status == "Cancelled":
		event_doc.status = "Cancelled"
	elif appointment_doc.status == "Completed":
		event_doc.status = "Completed"
	else:
		event_doc.status = "Open"

	event_doc.save(ignore_permissions=True)


def _build_event_description(appointment_doc, property_doc, customer_doc) -> str:
	lines = [
		_("Property: {0} ({1})").format(property_doc.title or property_doc.name, property_doc.name),
		_("Customer: {0}").format(customer_doc.full_name),
	]

	if property_doc.address_line1 or property_doc.city:
		address_parts = [
			property_doc.address_line1 or "",
			property_doc.city or "",
			property_doc.state or "",
			property_doc.country or "",
		]
		address = ", ".join([part for part in address_parts if part])
		if address:
			lines.append(_("Address: {0}").format(address))

	if appointment_doc.notes:
		lines.append(_("Notes: {0}").format(appointment_doc.notes))

	return "\n".join(lines)

