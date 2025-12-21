from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, get_time, add_to_date

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


@frappe.whitelist(allow_guest=True)
def get_agent_available_slots(agent_id: str) -> dict[str, Any]:
	"""Public API to get available appointment slots for an agent - no authentication required"""
	agent_doc = frappe.get_doc("Agent", agent_id)
	agent_doc.flags.ignore_permissions = True
	
	# Check agent verification only if mandate_agent_verification setting is enabled
	if utils.get_mandate_agent_verification():
		if agent_doc.status != "Verified":
			frappe.throw(_("Agent is not verified or not available."), frappe.PermissionError)

	start_date = frappe.form_dict.get("start_date")
	end_date = frappe.form_dict.get("end_date")
	
	if start_date:
		start_date = getdate(start_date)
	else:
		start_date = getdate()
	
	if end_date:
		end_date = getdate(end_date)
	else:
		end_date = add_to_date(start_date, days=7)

	available_slots = _calculate_available_slots(agent_doc, start_date, end_date)
	
	return {
		"agent_id": agent_id,
		"max_appointment_minutes": agent_doc.max_appointment_minutes or 30,
		"start_date": str(start_date),
		"end_date": str(end_date),
		"available_slots": available_slots,
	}


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

	agent_doc = frappe.get_doc("Agent", agent_name)
	
	# Check agent verification only if mandate_agent_verification setting is enabled
	if utils.get_mandate_agent_verification():
		if agent_doc.status != "Verified":
			frappe.throw(_("Agent is not verified."))

	customer = utils.get_customer_by_user(utils.get_current_user())
	if not customer:
		frappe.throw(_("Customer profile is required to book an appointment."))

	start_datetime = get_datetime(data["start_datetime"])
	end_datetime = get_datetime(data["end_datetime"])

	# Validate slot availability
	_validate_slot_availability(agent_doc, start_datetime, end_datetime)

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

	# Notifications are automatically created in Property Appointment doctype controller
	# (after_insert method handles creation notifications)

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
	# Notifications for reschedule are automatically created in Property Appointment doctype controller
	# (on_update method detects datetime changes and sends reschedule notifications)
	return serialize_appointment(doc.name)


@frappe.whitelist()
@utils.require_jwt()
def cancel_appointment(appointment_id: str) -> dict[str, Any]:
	doc = _ensure_appointment_access(appointment_id)
	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)
	_update_calendar_event(doc)
	# Notifications for cancellation are automatically created in Property Appointment doctype controller
	# (on_update method detects status changes and sends cancellation notifications)
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


def _calculate_available_slots(agent_doc, start_date, end_date) -> list[dict[str, Any]]:
	"""
	Calculate available appointment slots based on agent availability and existing appointments.
	
	Note: Availability slots are agent-specific - each agent has their own availability_slots
	child table entries. This function only calculates slots for the provided agent_doc.
	"""
	available_slots = []
	max_minutes = agent_doc.max_appointment_minutes or 30
	
	# Get THIS specific agent's availability slots from their child table
	# Each agent has their own independent availability schedule
	availability_slots = agent_doc.get("availability_slots", [])
	if not availability_slots:
		return []
	
	# Get existing scheduled appointments
	existing_appointments = frappe.get_all(
		"Property Appointment",
		filters={
			"agent": agent_doc.name,
			"status": "Scheduled",
			"start_datetime": [">=", datetime.combine(start_date, datetime.min.time())],
			"end_datetime": ["<=", datetime.combine(end_date, datetime.max.time())],
		},
		fields=["start_datetime", "end_datetime"],
	)
	
	# Create a set of booked time ranges
	booked_ranges = [
		(get_datetime(apt.start_datetime), get_datetime(apt.end_datetime))
		for apt in existing_appointments
	]
	
	# Map day names to weekday numbers (Monday = 0, Sunday = 6)
	day_map = {
		"Monday": 0,
		"Tuesday": 1,
		"Wednesday": 2,
		"Thursday": 3,
		"Friday": 4,
		"Saturday": 5,
		"Sunday": 6,
	}
	
	# Generate slots for each day in the range
	current_date = start_date
	while current_date <= end_date:
		weekday = current_date.weekday()
		
		# Find availability slots for this day
		for avail_slot in availability_slots:
			if day_map.get(avail_slot.day_of_week) == weekday:
				slot_start_time = get_time(avail_slot.start_time)
				slot_end_time = get_time(avail_slot.end_time)
				
				slot_start_datetime = datetime.combine(current_date, slot_start_time)
				slot_end_datetime = datetime.combine(current_date, slot_end_time)
				
				# Generate appointment slots within this availability window
				current_slot_start = slot_start_datetime
				while current_slot_start + timedelta(minutes=max_minutes) <= slot_end_datetime:
					current_slot_end = current_slot_start + timedelta(minutes=max_minutes)
					
					# Check if this slot conflicts with existing appointments
					is_available = True
					for booked_start, booked_end in booked_ranges:
						if not (current_slot_end <= booked_start or current_slot_start >= booked_end):
							is_available = False
							break
					
					if is_available:
						available_slots.append({
							"start_datetime": current_slot_start.strftime("%Y-%m-%d %H:%M:%S"),
							"end_datetime": current_slot_end.strftime("%Y-%m-%d %H:%M:%S"),
							"date": str(current_date),
							"time": current_slot_start.strftime("%H:%M"),
						})
					
					# Move to next slot (increment by appointment duration)
					current_slot_start += timedelta(minutes=max_minutes)
		
		current_date += timedelta(days=1)
	
	# Sort by datetime
	available_slots.sort(key=lambda x: x["start_datetime"])
	return available_slots


def _validate_slot_availability(agent_doc, start_datetime: datetime, end_datetime: datetime):
	"""
	Validate that the requested slot is available for the specific agent.
	
	Note: Availability validation is agent-specific - it checks against the provided
	agent_doc's availability_slots child table entries.
	"""
	max_minutes = agent_doc.max_appointment_minutes or 30
	
	# Check duration
	duration_minutes = (end_datetime - start_datetime).total_seconds() / 60
	if abs(duration_minutes - max_minutes) > 0.1:  # Allow small floating point differences
		frappe.throw(
			_("Appointment duration must be exactly {0} minutes.").format(max_minutes),
			frappe.ValidationError,
		)
	
	# Check if THIS specific agent has availability slots defined
	# Availability slots are stored in the agent's child table, so they're agent-specific
	availability_slots = agent_doc.get("availability_slots", [])
	if not availability_slots:
		frappe.throw(_("Agent has no availability slots configured."), frappe.ValidationError)
	
	# Map day names to weekday numbers
	day_map = {
		"Monday": 0,
		"Tuesday": 1,
		"Wednesday": 2,
		"Thursday": 3,
		"Friday": 4,
		"Saturday": 5,
		"Sunday": 6,
	}
	
	requested_date = start_datetime.date()
	requested_weekday = requested_date.weekday()
	requested_start_time = start_datetime.time()
	requested_end_time = end_datetime.time()
	
	# Check if slot falls within agent's availability and aligns with slot boundaries
	is_valid_slot = False
	for avail_slot in availability_slots:
		if day_map.get(avail_slot.day_of_week) == requested_weekday:
			slot_start_time = get_time(avail_slot.start_time)
			slot_end_time = get_time(avail_slot.end_time)
			
			# Check if requested time falls within availability window
			if slot_start_time <= requested_start_time and requested_end_time <= slot_end_time:
				# Check if slot start aligns with appointment duration boundaries
				# Calculate how many minutes from availability start
				slot_start_datetime = datetime.combine(requested_date, slot_start_time)
				minutes_from_start = (start_datetime - slot_start_datetime).total_seconds() / 60
				
				# Check if minutes_from_start is a multiple of max_minutes
				if minutes_from_start >= 0 and (minutes_from_start % max_minutes) < 0.1:
					is_valid_slot = True
					break
	
	if not is_valid_slot:
		frappe.throw(
			_("The requested time slot is not within the agent's available hours or does not align with available slot boundaries."),
			frappe.ValidationError,
		)
	
	# Check for conflicts with existing appointments
	conflicting = frappe.db.sql(
		"""
		select name
		from `tabProperty Appointment`
		where agent = %s
		  and status = 'Scheduled'
		  and start_datetime < %s
		  and end_datetime > %s
		""",
		(agent_doc.name, end_datetime, start_datetime),
	)
	
	if conflicting:
		frappe.throw(
			_("The requested time slot conflicts with an existing appointment."),
			frappe.ValidationError,
		)

