from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_time

from . import properties, utils

SUMMARY_FIELDS = [
	"name",
	"full_name",
	"status",
	"phone",
	"whatsapp_number",
	"bio",
	"profile_image",
]


@frappe.whitelist(allow_guest=True)
def list_agents() -> dict[str, Any]:
	"""Public API to list agents - no authentication required"""
	page = cint(frappe.form_dict.get("page") or 1)
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	status = (frappe.form_dict.get("status") or "").strip()
	search = (frappe.form_dict.get("search") or "").strip()

	page = max(1, page)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size

	filters: list[list[Any]] = []
	if status:
		filters.append(["Agent", "status", "=", status])
	# else:
	# 	filters.append(["Agent", "status", "=", "Verified"])

	if search:
		filters.append(["Agent", "full_name", "like", f"%{search}%"])

	items = frappe.get_all(
		"Agent",
		filters=filters,
		fields=SUMMARY_FIELDS,
		start=start,
		limit=page_size,
		order_by="modified desc",
		ignore_permissions=True,
	)

	# For public API, we need to bypass permissions for count
	# frappe.db.count() doesn't support ignore_permissions, so we temporarily set user to Administrator
	# This ensures we get the same filtered count as the items above
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		total_items = frappe.db.count("Agent", filters, cache=False)
	finally:
		frappe.set_user(original_user)
	total_pages = (total_items + page_size - 1) // page_size if page_size else 0

	property_counts = _get_agent_property_counts([row["name"] for row in items])

	return {
		"items": [
			{
				**_serialize_agent_summary(row),
				"property_count": property_counts.get(row["name"], 0),
			}
			for row in items
		],
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


@frappe.whitelist(allow_guest=True)
def get_agent(agent_id: str) -> dict[str, Any]:
	"""Public API to get agent details - no authentication required"""
	frappe.set_user("Administrator")
	agent_name = frappe.db.get_value("Agent", {"dfd_registration_id": agent_id}, "name")
	if not agent_name:
		agent_name = frappe.db.get_value("Agent", {"name": agent_id}, "name")
	if not agent_name:
		frappe.throw(_("Agent not found."), frappe.DoesNotExistError)
		
	doc = frappe.get_doc("Agent", agent_name)
	doc.flags.ignore_permissions = True
	
	# Ensure child tables are loaded
	if hasattr(doc, "availability_slots") and not doc.availability_slots:
		doc.load_from_db()

	# Check agent verification only if mandate_agent_verification setting is enabled
	if utils.get_mandate_agent_verification():
		if doc.status != "Verified":
			frappe.throw(_("Agent is not verified or not available."), frappe.PermissionError)

	return _serialize_agent_detail(doc)


@frappe.whitelist()
@utils.require_jwt(roles={"Agent", "System Manager"})
def update_agent_availability() -> dict[str, Any]:
	"""
	Update agent availability slots and max appointment minutes.
	
	This endpoint updates availability slots specific to the logged-in agent.
	Availability slots are stored as a child table in the Agent doctype,
	ensuring each agent has their own unique availability schedule.
	
	Agents can only update their own availability (not other agents').
	System Managers can update any agent's availability.
	"""
	current_user = utils.get_current_user()
	
	# Get agent record for the current logged-in user
	# This ensures availability is always mapped to a specific agent, never global
	agent_name = frappe.db.get_value("Agent", {"user": current_user}, "name")
	
	if not agent_name:
		frappe.throw(_("Agent profile not found."), frappe.PermissionError)
	
	# Verify agent ownership - agents can only update their own availability
	# This prevents agents from modifying other agents' schedules
	if "System Manager" not in frappe.get_roles(current_user):
		agent_user = frappe.db.get_value("Agent", agent_name, "user")
		if agent_user != current_user:
			frappe.throw(_("You can only update your own availability. Availability is agent-specific."), frappe.PermissionError)
	
	data = utils.get_request_json()
	
	# Load the specific agent document - availability slots are stored as child table
	# Each agent has their own availability_slots child table entries
	agent_doc = frappe.get_doc("Agent", agent_name)
	
	# Check if availability_slots field exists in the doctype
	agent_meta = frappe.get_meta("Agent")
	has_availability_slots_field = agent_meta.has_field("availability_slots")
	
	# Update max_appointment_minutes if provided
	if "max_appointment_minutes" in data:
		if not agent_meta.has_field("max_appointment_minutes"):
			frappe.throw(_("max_appointment_minutes field is not available. Please ensure the Agent doctype has been migrated."), frappe.ValidationError)
		
		max_minutes = cint(data.get("max_appointment_minutes"))
		if max_minutes and max_minutes > 0:
			agent_doc.max_appointment_minutes = max_minutes
		else:
			frappe.throw(_("max_appointment_minutes must be a positive integer."), frappe.ValidationError)
	
	# Update availability slots if provided
	# Note: availability_slots is a child table field, so slots are specific to this agent
	# When we clear and set new slots, they are only for this agent's record
	if "availability_slots" in data:
		if not has_availability_slots_field:
			frappe.throw(_("availability_slots field is not available. Please ensure the Agent doctype has been migrated with the availability_slots child table."), frappe.ValidationError)
		availability_slots = data.get("availability_slots", [])
		if not isinstance(availability_slots, list):
			frappe.throw(_("availability_slots must be an array."), frappe.ValidationError)
		
		# Clear existing slots for THIS agent only
		# This ensures each agent has their own independent availability schedule
		agent_doc.set("availability_slots", [])
		
		# Valid day names
		valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
		
		# Add new slots
		for slot_data in availability_slots:
			if not isinstance(slot_data, dict):
				continue
			
			day_of_week = slot_data.get("day_of_week", "").strip()
			start_time_str = slot_data.get("start_time", "").strip()
			end_time_str = slot_data.get("end_time", "").strip()
			
			if not day_of_week or not start_time_str or not end_time_str:
				continue
			
			if day_of_week not in valid_days:
				frappe.throw(
					_("Invalid day_of_week: {0}. Must be one of: {1}").format(
						day_of_week, ", ".join(sorted(valid_days))
					),
					frappe.ValidationError,
				)
			
			try:
				start_time = get_time(start_time_str)
				end_time = get_time(end_time_str)
			except Exception:
				frappe.throw(
					_("Invalid time format. Use HH:MM:SS or HH:MM format."),
					frappe.ValidationError,
				)
			
			# Validate that end_time is after start_time
			if end_time <= start_time:
				frappe.throw(
					_("end_time must be after start_time for {0}").format(day_of_week),
					frappe.ValidationError,
				)
			
			# Append to THIS agent's availability_slots child table
			# This ensures the slot is associated only with this specific agent record
			# Use append method if field exists, otherwise handle gracefully
			try:
				agent_doc.append(
					"availability_slots",
					{
						"day_of_week": day_of_week,
						"start_time": start_time,
						"end_time": end_time,
					},
				)
			except AttributeError:
				frappe.throw(
					_("availability_slots field is not available. Please ensure the Agent doctype has been migrated with the Agent Availability Slot child table."),
					frappe.ValidationError,
				)
	
	# Save the agent document - this saves all child table entries (availability_slots)
	# Each agent has their own separate availability_slots child table entries
	agent_doc.save(ignore_permissions=True)
	
	return {
		"message": _("Agent availability updated successfully."),
		"agent": _serialize_agent_detail(agent_doc),
	}


def _serialize_agent_summary(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"id": row.get("name"),
		"name": row.get("full_name") or row.get("name"),
		"status": row.get("status"),
		"bio": row.get("bio"),
		"phone": row.get("phone"),
		"whatsapp_number": row.get("whatsapp_number"),
		"profile_image": row.get("profile_image"),
	}


def _serialize_agent_detail(doc) -> dict[str, Any]:
	# Use raw SQL to avoid permission issues for public API
	result = frappe.db.sql(
		"""
		SELECT {fields}
		FROM `tabProperty`
		WHERE status = 'Active' AND agent = %(agent_name)s
		ORDER BY modified DESC
		LIMIT 50
		""".format(fields=", ".join(properties.SUMMARY_FIELDS)),
		{"agent_name": doc.name},
		as_dict=True,
	)
	properties_list = list(result)

	# Get availability slots
	availability_slots = []
	if hasattr(doc, "availability_slots"):
		try:
			if doc.availability_slots:
				for slot in doc.availability_slots:
					availability_slots.append({
						"day_of_week": slot.day_of_week,
						"start_time": str(slot.start_time) if slot.start_time else None,
						"end_time": str(slot.end_time) if slot.end_time else None,
					})
		except (AttributeError, TypeError):
			# Field might not exist if migration hasn't run yet
			pass

	# Get rating statistics
	try:
		from . import reviews
		rating_stats = reviews.get_agent_rating_stats(doc.name)
	except Exception:
		# If reviews module not available or error, return empty stats
		rating_stats = {
			"average_overall_rating": 0.0,
			"average_agent_rating": 0.0,
			"average_property_rating": 0.0,
			"total_reviews": 0,
			"recent_reviews": [],
		}

	return {
		"id": doc.name,
		"name": doc.full_name or doc.name,
		"status": doc.status,
		"bio": doc.bio,
		"phone": doc.phone,
		"whatsapp_number": doc.whatsapp_number,
		"profile_image": doc.profile_image,
		"max_daily_appointments": doc.max_daily_appointments or 10,
		"max_appointment_minutes": getattr(doc, "max_appointment_minutes", None) or 30,
		"availability_slots": availability_slots,
		"property_count": len(properties_list),
		"properties": [properties.serialize_property_summary(row) for row in properties_list],
		"ratings": rating_stats,
	}


def _get_agent_property_counts(agent_ids: list[str]) -> dict[str, int]:
	if not agent_ids:
		return {}

	counts: dict[str, int] = {}
	if agent_ids:
		# Use raw SQL query to avoid permission issues for public API
		placeholders = ",".join(["%s"] * len(agent_ids))
		result = frappe.db.sql(
			f"""
			SELECT agent, COUNT(name) as total
			FROM `tabProperty`
			WHERE status = 'Active' AND agent IN ({placeholders})
			GROUP BY agent
			""",
			tuple(agent_ids),
			as_dict=True,
		)
		for row in result:
			agent = row.get("agent")
			if agent:
				counts[agent] = int(row.get("total") or 0)
	return counts
