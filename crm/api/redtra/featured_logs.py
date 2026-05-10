from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import get_datetime


FEATURED_LOG_EVENT_OPTIONS = {"Activated", "Updated", "Deactivated", "Expired"}
FEATURED_LOG_SOURCE_OPTIONS = {"Desk", "API", "Billing", "Scheduler"}


def create_property_featured_log(
	property_id: str,
	*,
	agent: str | None = None,
	event_type: str,
	source: str,
	featured_from: Any = None,
	featured_until: Any = None,
	notes: str | None = None,
	triggered_by: str | None = None,
) -> None:
	if event_type not in FEATURED_LOG_EVENT_OPTIONS:
		return
	if source not in FEATURED_LOG_SOURCE_OPTIONS:
		return
	if not property_id:
		return

	property_agent = agent or frappe.db.get_value("Property", property_id, "agent")
	if not property_agent:
		return

	doc = frappe.get_doc(
		{
			"doctype": "Property Featured Log",
			"property": property_id,
			"agent": property_agent,
			"event_type": event_type,
			"source": source,
			"featured_from": _to_datetime_or_none(featured_from),
			"featured_until": _to_datetime_or_none(featured_until),
			"notes": notes,
			"triggered_by": triggered_by or frappe.session.user,
		}
	)
	doc.insert(ignore_permissions=True)


def infer_featured_event_type(previous: dict[str, Any] | None, current: dict[str, Any]) -> str | None:
	prev_is_featured = bool(_get(previous, "is_featured")) if previous else False
	curr_is_featured = bool(_get(current, "is_featured"))

	prev_from = _to_datetime_or_none(_get(previous, "featured_from")) if previous else None
	prev_until = _to_datetime_or_none(_get(previous, "featured_until")) if previous else None
	curr_from = _to_datetime_or_none(_get(current, "featured_from"))
	curr_until = _to_datetime_or_none(_get(current, "featured_until"))

	if not prev_is_featured and curr_is_featured:
		return "Activated"
	if prev_is_featured and not curr_is_featured:
		return "Deactivated"
	if (
		prev_is_featured == curr_is_featured
		and prev_from == curr_from
		and prev_until == curr_until
	):
		return None
	return "Updated"


def _get(payload: dict[str, Any] | None, key: str) -> Any:
	if not payload:
		return None
	if hasattr(payload, "get"):
		return payload.get(key)
	return None


def _to_datetime_or_none(value: Any):
	if not value:
		return None
	try:
		return get_datetime(value)
	except Exception:
		return None
