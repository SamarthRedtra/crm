from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_time
from frappe.query_builder import DocType, functions as fn

from . import properties, reviews, utils

SUMMARY_FIELDS = [
	"name",
	"full_name",
	"status",
	"phone",
	"whatsapp_number",
	"bio",
	"profile_image",
	"agency",
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

	agent_ids = [row["name"] for row in items]
	property_counts = _get_agent_property_counts(agent_ids)
	leads_counts = _get_agent_leads_counts(agent_ids)
	ratings_by_agent = reviews.get_agent_rating_stats_batch(agent_ids)

	return {
		"items": [
			_serialize_agent_summary({
				**row,
				"property_count": property_counts.get(row["name"], 0),
				"leads": leads_counts.get(row["name"], 0),
				"ratings": ratings_by_agent.get(row["name"], reviews.empty_agent_rating_summary()),
			})
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
		"message": _("Agent availability updated successfully. This update applies only to your agent profile."),
		"agent_id": agent_doc.name,
		"agent_name": agent_doc.full_name or agent_doc.name,
		"agent": _serialize_agent_detail(agent_doc),
		"note": _("Availability slots are agent-specific. Each agent manages their own schedule independently."),
	}


def _serialize_agent_summary(row: dict[str, Any]) -> dict[str, Any]:
	# Get agency details if available
	agency_details = None
	agency_id = row.get("agency")
	if agency_id:
		try:
			from . import agencies
			agency_details = agencies.get_agency_details(agency_id)
		except Exception:
			pass

	whatsapp_link = _build_whatsapp_link(row.get("whatsapp_number") or row.get("phone"))

	return {
		"id": row.get("name"),
		"name": row.get("full_name") or row.get("name"),
		"status": row.get("status"),
		"bio": row.get("bio"),
		"phone": row.get("phone"),
		"whatsapp_number": row.get("whatsapp_number"),
		"whatsapp_link": whatsapp_link,
		"profile_image": row.get("profile_image"),
		"agency": agency_details,
		# Optional fields that might be added by batch processing
		"property_count": row.get("property_count", 0),
		"leads": row.get("leads", 0),
		"ratings": row.get("ratings") or reviews.empty_agent_rating_summary(),
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
	property_ids = [row.get("name") for row in properties_list if row.get("name")]
	active_property_count = frappe.db.count("Property", {"status": "Active", "agent": doc.name})
	activity_stats = _get_agent_activity_stats(doc.name)
	expertise = _get_agent_expertise(doc.name)

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
		rating_stats = reviews.get_agent_rating_stats(doc.name)
	except Exception:
		rating_stats = reviews.empty_agent_rating_summary()

	# Get agency details if available
	agency_details = None
	agency_id = getattr(doc, "agency", None)
	if agency_id:
		try:
			from . import agencies
			agency_details = agencies.get_agency_details(agency_id)
		except Exception:
			pass

	whatsapp_link = _build_whatsapp_link(doc.whatsapp_number or doc.phone)

	return {
		"id": doc.name,
		"name": doc.full_name or doc.name,
		"status": doc.status,
		"bio": doc.bio,
		"phone": doc.phone,
		"whatsapp_number": doc.whatsapp_number,
		"whatsapp_link": whatsapp_link,
		"profile_image": doc.profile_image,
		"brn_id": doc.dfd_registration_id,
		"active_properties": active_property_count,
		"property_ids": property_ids,
		"sales": activity_stats.get("sales", 0),
		"leads": activity_stats.get("leads", 0),
		"expertise": expertise,
		"max_daily_appointments": doc.max_daily_appointments or 10,
		"max_appointment_minutes": getattr(doc, "max_appointment_minutes", None) or 30,
		"availability_slots": availability_slots,
		"property_count": len(properties_list),
		"properties": [properties.serialize_property_summary(row) for row in properties_list],
		"ratings": rating_stats,
		"agency": agency_details,
	}


def _get_agent_property_counts(agent_ids: list[str]) -> dict[str, int]:
	if not agent_ids:
		return {}

	counts: dict[str, int] = {}
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


def _get_agent_leads_counts(agent_ids: list[str]) -> dict[str, int]:
	if not agent_ids:
		return {}

	counts: dict[str, int] = {}
	placeholders = ",".join(["%s"] * len(agent_ids))
	result = frappe.db.sql(
		f"""
		SELECT agent, COUNT(name) as total
		FROM `tabProperty Appointment`
		WHERE agent IN ({placeholders})
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


def _build_whatsapp_link(number: str | None) -> str | None:
	if not number:
		return None
	clean_number = str(number).replace("+", "").replace(" ", "")
	return f"https://wa.me/{clean_number}" if clean_number else None


def _get_agent_activity_stats(agent_id: str) -> dict[str, Any]:
	# Count properties marked as sold for this agent
	sales_count = frappe.db.count(
		"Property", 
		{"agent": agent_id, "is_sold": 1}
	)
	leads_count = frappe.db.count("Property Appointment", {"agent": agent_id})
	return {"sales": sales_count, "leads": leads_count}


def _get_agent_expertise(agent_id: str) -> dict[str, Any]:
	prop = DocType("Property")
	property_type_rows = (
		frappe.qb.from_(prop)
		.select(prop.property_type.as_("property_type"), fn.Count(prop.name).as_("total"))
		.where((prop.status == "Active") & (prop.agent == agent_id))
		.groupby(prop.property_type)
		.run(as_dict=True)
	)
	category_rows = (
		frappe.qb.from_(prop)
		.select(prop.property_category.as_("property_category"), fn.Count(prop.name).as_("total"))
		.where((prop.status == "Active") & (prop.agent == agent_id))
		.groupby(prop.property_category)
		.run(as_dict=True)
	)

	def _top_values(rows: list[dict[str, Any]]) -> list[str]:
		sorted_rows = sorted(rows, key=lambda row: int(row.get("total") or 0), reverse=True)
		values = []
		for row in sorted_rows:
			value = row.get("property_type") or row.get("property_category")
			if value:
				values.append(value)
		return values

	return {
		"property_types": _top_values(property_type_rows),
		"property_categories": _top_values(category_rows),
	}
