from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from . import utils


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def subscribe_push_token() -> dict[str, Any]:
	data = utils.get_request_json(["fcm_token", "environment"])
	from raven.api import notification as raven_notification

	raven_notification.subscribe(
		fcm_token=data.get("fcm_token"),
		environment=data.get("environment"),
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
	from raven import notification as raven_notification

	raven_notification.send_notification_to_user(
		user_id=data.get("user_id"),
		title=data.get("title"),
		message=data.get("message"),
		data=data.get("data") or {},
		user_image_path=data.get("user_image_path"),
	)
	return {"message": _("Push notification sent."), "ok": True}


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

