from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime

from . import properties, reviews

MAX_FEATURED_PROPERTIES = 8
MAX_HOME_ITEMS = 8


@frappe.whitelist(allow_guest=True)
def get_home() -> dict[str, Any]:
	featured_properties = _get_featured_properties()
	areas = _get_top_areas()
	developers = _get_top_developers()
	agents = _get_top_agents()

	return {
		"featured_properties": featured_properties,
		"areas": areas,
		"developers": developers,
		"agents": agents,
	}


def _get_featured_properties() -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Property",
		filters={
			"status": "Active",
			"is_featured": 1,
			"featured_until": [">=", now_datetime()],
		},
		fields=properties.SUMMARY_FIELDS,
		order_by="modified desc",
		limit=MAX_FEATURED_PROPERTIES,
		ignore_permissions=True,
	)

	if len(rows) < MAX_FEATURED_PROPERTIES:
		additional_rows = frappe.get_all(
			"Property",
			filters={"status": "Active", "name": ["not in", [row["name"] for row in rows]]},
			or_filters={
				"is_featured": 0,
				"featured_until": [">=", now_datetime()],
			},
			fields=properties.SUMMARY_FIELDS,
			order_by="modified desc",
			limit=MAX_FEATURED_PROPERTIES - len(rows),
			ignore_permissions=True,
		)
		rows.extend(additional_rows)

	return [properties.serialize_property_summary(row) for row in rows]


def _get_top_areas() -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Area",
		fields=["name", "area_name", "city", "state", "country", "latitude", "longitude"],
		order_by="area_name asc",
		limit=MAX_HOME_ITEMS,
		ignore_permissions=True,
	)

	return [
		{
			"id": row["name"],
			"area_name": row.get("area_name"),
			"city": row.get("city"),
			"state": row.get("state"),
			"country": row.get("country"),
			"latitude": row.get("latitude"),
			"longitude": row.get("longitude"),
		}
		for row in rows
	]


def _get_top_developers() -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Developer",
		filters={"status": "Active"},
		fields=[
			"name",
			"developer_name",
			"city",
			"state",
			"country",
			"logo",
			"website",
		],
		order_by="modified desc",
		limit=MAX_HOME_ITEMS,
		ignore_permissions=True,
	)

	property_counts = {}
	if rows:
		property_counts = {
			row["developer"]: int(row.get("total") or 0)
			for row in frappe.get_all(
				"Property",
				filters={"status": "Active", "developer": ["in", [item["name"] for item in rows]]},
				fields=["developer", {"COUNT": "name", "as": "total"}],
				group_by="developer",
				ignore_permissions=True,
			)
		}

	return [
		{
			"id": row["name"],
			"name": row.get("developer_name"),
			"city": row.get("city"),
			"state": row.get("state"),
			"country": row.get("country"),
			"logo": row.get("logo"),
			"website": row.get("website"),
			"property_count": property_counts.get(row["name"], 0),
		}
		for row in rows
	]


def _get_top_agents() -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Agent",
		filters={"status": "Verified"},
		fields=["name", "full_name", "bio", "phone", "whatsapp_number", "profile_image"],
		order_by="modified desc",
		limit=MAX_HOME_ITEMS,
		ignore_permissions=True,
	)

	property_counts = {}
	if rows:
		property_counts = {
			row["agent"]: int(row.get("total") or 0)
			for row in frappe.get_all(
				"Property",
				filters={"status": "Active", "agent": ["in", [item["name"] for item in rows]]},
				fields=["agent", {"COUNT": "name", "as": "total"}],
				group_by="agent",
				ignore_permissions=True,
			)
		}

	agent_ids = [row["name"] for row in rows]
	ratings_by_agent = reviews.get_agent_rating_stats_batch(agent_ids)

	return [
		{
			"id": row["name"],
			"name": row.get("full_name") or row.get("name"),
			"bio": row.get("bio"),
			"phone": row.get("phone"),
			"whatsapp_number": row.get("whatsapp_number"),
			"profile_image": row.get("profile_image"),
			"property_count": property_counts.get(row["name"], 0),
			"ratings": ratings_by_agent.get(row["name"], reviews.empty_agent_rating_summary()),
		}
		for row in rows
	]
