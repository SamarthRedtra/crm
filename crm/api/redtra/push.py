from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from . import utils


def _normalize_push_environment(environment: str) -> str:
	"""Map mobile app values to Raven Push Token options (Web | Mobile)."""
	normalized = (environment or "").strip().lower()
	if normalized in {"mobile", "production", "development", "android", "ios"}:
		return "Mobile"
	if normalized == "web":
		return "Web"
	return environment


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def subscribe_push_token() -> dict[str, Any]:
	data = utils.get_request_json(["fcm_token", "environment"])
	from raven.api import notification as raven_notification

	raven_notification.subscribe(
		fcm_token=data.get("fcm_token"),
		environment=_normalize_push_environment(data.get("environment")),
		device_information=data.get("device_information"),
	)
	return {"message": _("Subscribed"), "ok": True}


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def unsubscribe_push_token() -> dict[str, Any]:
	data = utils.get_request_json(["fcm_token"])
	from raven.api import notification as raven_notification

	raven_notification.unsubscribe(fcm_token=data.get("fcm_token"))
	return {"message": _("Unsubscribed"), "ok": True}


@frappe.whitelist(methods=["POST"])
@utils.require_jwt(roles={"System Manager", "Agency Admin", "Agency Manager"})
def send_push_notification() -> dict[str, Any]:
	data = utils.get_request_json(["user_id", "title", "message"])
	from crm.api.redtra.fcm import is_darify_firebase_enabled, send_push_to_user

	user_id = data.get("user_id")
	push_data = data.get("data") or {}
	push_data["base_url"] = frappe.utils.get_url()
	push_data["sitename"] = frappe.local.site

	if is_darify_firebase_enabled():
		return send_push_to_user(
			user_id=user_id,
			title=data.get("title"),
			message=data.get("message"),
			data=push_data,
		)

	from frappe.push_notification import PushNotification

	push_notification = PushNotification("raven")
	relay_enabled = push_notification.is_enabled()
	token_count = frappe.db.count("Raven Push Token", {"user": user_id})

	if not relay_enabled:
		return {
			"ok": False,
			"sent": False,
			"relay_enabled": False,
			"token_count": token_count,
			"message": _("Push Notification Relay is disabled on this site."),
		}

	try:
		sent = push_notification.send_notification_to_user(
			user_id=user_id,
			title=data.get("title"),
			body=data.get("message"),
			data=push_data,
		)
	except Exception as exc:
		frappe.log_error(title="CRM push send failed", message=frappe.get_traceback())
		return {
			"ok": False,
			"sent": False,
			"relay_enabled": True,
			"token_count": token_count,
			"message": str(exc) or _("Failed to send push notification."),
		}

	if not sent:
		return {
			"ok": False,
			"sent": False,
			"relay_enabled": True,
			"token_count": token_count,
			"message": _(
				"Relay rejected the send request. Check Error Log and Push Notification Settings."
			),
		}

	return {
		"ok": True,
		"sent": True,
		"relay_enabled": True,
		"token_count": token_count,
		"message": _("Push notification sent."),
	}


@frappe.whitelist(methods=["POST"])
@utils.require_jwt(roles={"System Manager", "Agency Admin", "Agency Manager"})
def send_group_push_notification() -> dict[str, Any]:
	data = utils.get_request_json(["group_id", "title", "message"])
	from raven import notification as raven_notification

	raven_notification.send_notification_to_topic(
		channel_id=data.get("group_id"),
		title=data.get("title"),
		message=data.get("message"),
		data=data.get("data") or {},
		user_image_path=data.get("user_image_path"),
	)
	return {"message": _("Group push notification sent."), "ok": True}

