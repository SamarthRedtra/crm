from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.query_builder import DocType, Order, functions as fn
from frappe.utils import cint

from . import utils


@frappe.whitelist()
@utils.require_jwt()
def list_notifications() -> dict[str, Any]:
	page = max(1, cint(frappe.form_dict.get("page") or 1))
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page_size = max(1, min(page_size, 100))
	offset = (page - 1) * page_size
	unread_only = _coerce_bool(frappe.form_dict.get("unread_only"))

	user = utils.get_current_user()
	Notification = DocType("CRM Notification")

	query = (
		frappe.qb.from_(Notification)
		.select(
			Notification.name.as_("id"),
			Notification.creation.as_("created_at"),
			Notification.from_user,
			Notification.type,
			Notification.notification_text,
			Notification.message,
			Notification.notification_type_doctype,
			Notification.notification_type_doc,
			Notification.reference_doctype,
			Notification.reference_name,
			Notification.read,
		)
		.where(Notification.to_user == user)
		.orderby(Notification.creation, order=Order.desc)
		.offset(offset)
		.limit(page_size)
	)

	if unread_only:
		query = query.where(Notification.read == 0)

	count_query = (
		frappe.qb.from_(Notification)
		.select(fn.Count(Notification.name))
		.where(Notification.to_user == user)
	)
	if unread_only:
		count_query = count_query.where(Notification.read == 0)

	total_count = int(count_query.run()[0][0] or 0)

	notifications = []
	for row in query.run(as_dict=True):
		notifications.append(_serialize_notification(row))

	return {
		"items": notifications,
		"page": page,
		"page_size": page_size,
		"total_items": total_count,
		"total_pages": (total_count + page_size - 1) // page_size if page_size else 0,
	}


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def mark_notifications_read() -> dict[str, Any]:
	payload = utils.get_request_json()
	notification_ids = payload.get("notification_ids") or []
	mark_all = not notification_ids

	user = utils.get_current_user()

	filters: dict[str, Any] = {"to_user": user, "read": 0}
	if not mark_all:
		filters["name"] = ["in", notification_ids]

	names = frappe.get_all("CRM Notification", filters=filters, pluck="name")
	for name in names:
		frappe.db.set_value("CRM Notification", name, "read", 1, update_modified=False)

	return {"updated": len(names)}


@frappe.whitelist(methods=["DELETE"])
@utils.require_jwt()
def delete_notification(notification_id: str) -> dict[str, Any]:
	user = utils.get_current_user()

	if not frappe.db.exists("CRM Notification", {"name": notification_id, "to_user": user}):
		frappe.throw(_("Notification not found"), frappe.DoesNotExistError)

	frappe.db.delete("CRM Notification", notification_id)
	return {"message": "Notification deleted successfully"}


def _serialize_notification(row: dict[str, Any]) -> dict[str, Any]:
	from_user = row.get("from_user")
	return {
		"id": row.get("id"),
		"created_at": row.get("created_at"),
		"type": row.get("type"),
		"title": row.get("notification_text"),
		"message": row.get("message"),
		"read": bool(row.get("read")),
		"from_user": {
			"id": from_user,
			"full_name": frappe.db.get_value("User", from_user, "full_name") if from_user else None,
		},
		"reference": {
			"doctype": row.get("reference_doctype") or row.get("notification_type_doctype"),
			"name": row.get("reference_name") or row.get("notification_type_doc"),
		},
	}


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
