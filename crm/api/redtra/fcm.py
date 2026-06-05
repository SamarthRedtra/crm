from __future__ import annotations

import json
from typing import Any

import frappe
import google.auth.transport.requests
import requests
from frappe import _
from google.oauth2 import service_account

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
INVALID_TOKEN_ERRORS = {
	"UNREGISTERED",
	"NOT_FOUND",
}


def is_darify_firebase_enabled() -> bool:
	return (
		frappe.db.get_single_value("FCRM Settings", "mobile_push_provider") == "Darify Firebase"
	)


def _get_settings():
	return frappe.get_single("FCRM Settings")


def _get_service_account_info() -> dict[str, Any]:
	settings = _get_settings()
	raw = settings.get_password("firebase_service_account_json")
	if not raw:
		frappe.throw(_("Firebase Service Account JSON is not configured in FCRM Settings."))

	try:
		info = json.loads(raw)
	except json.JSONDecodeError as exc:
		frappe.throw(_("Firebase Service Account JSON is invalid: {0}").format(exc))

	if not info.get("private_key") or not info.get("client_email"):
		frappe.throw(_("Firebase Service Account JSON must include private_key and client_email."))

	return info


def _get_access_token() -> str:
	info = _get_service_account_info()
	credentials = service_account.Credentials.from_service_account_info(
		info, scopes=[FCM_SCOPE]
	)
	credentials.refresh(google.auth.transport.requests.Request())
	return credentials.token


def _stringify_data(data: dict[str, Any] | None) -> dict[str, str]:
	if not data:
		return {}

	stringified: dict[str, str] = {}
	for key, value in data.items():
		if value is None:
			continue
		stringified[str(key)] = value if isinstance(value, str) else json.dumps(value)
	return stringified


def _delete_invalid_token(token: str) -> None:
	name = frappe.db.exists("Raven Push Token", {"fcm_token": token})
	if name:
		frappe.delete_doc("Raven Push Token", name, ignore_permissions=True)


def send_to_token(
	token: str,
	title: str,
	body: str,
	data: dict[str, Any] | None = None,
) -> dict[str, Any]:
	settings = _get_settings()
	project_id = settings.firebase_project_id
	if not project_id:
		frappe.throw(_("Firebase Project ID is not configured in FCRM Settings."))

	payload = {
		"message": {
			"token": token,
			"notification": {"title": title, "body": body},
			"data": _stringify_data(data),
			"android": {"priority": "high"},
		}
	}

	response = requests.post(
		FCM_SEND_URL.format(project_id=project_id),
		headers={
			"Authorization": f"Bearer {_get_access_token()}",
			"Content-Type": "application/json",
		},
		json=payload,
		timeout=settings.firebase_request_timeout_seconds or 15,
	)

	try:
		response_json = response.json()
	except ValueError:
		response_json = {"raw": response.text}

	result = {
		"token": token,
		"success": response.ok,
		"status_code": response.status_code,
		"response": response_json,
	}

	if not response.ok:
		error_status = (
			response_json.get("error", {}).get("status")
			or response_json.get("error", {}).get("details", [{}])[0].get("errorCode")
		)
		if error_status in INVALID_TOKEN_ERRORS:
			_delete_invalid_token(token)
			result["token_removed"] = True

	return result


def send_push_to_user(
	user_id: str,
	title: str,
	message: str,
	data: dict[str, Any] | None = None,
) -> dict[str, Any]:
	if not is_darify_firebase_enabled():
		frappe.throw(_("Darify Firebase push provider is not enabled."))

	tokens = frappe.get_all(
		"Raven Push Token",
		filters={"user": user_id},
		pluck="fcm_token",
	)

	if not tokens:
		return {
			"ok": False,
			"sent": False,
			"provider": "Darify Firebase",
			"token_count": 0,
			"sent_count": 0,
			"failed_count": 0,
			"message": _("No registered FCM tokens found for this user."),
		}

	results = [
		send_to_token(token=token, title=title, body=message, data=data) for token in tokens
	]
	sent_count = sum(1 for result in results if result.get("success"))
	failed_count = len(results) - sent_count

	return {
		"ok": sent_count > 0,
		"sent": sent_count > 0,
		"provider": "Darify Firebase",
		"token_count": len(tokens),
		"sent_count": sent_count,
		"failed_count": failed_count,
		"results": results,
		"message": _("Push notification sent to {0} device(s).").format(sent_count)
		if sent_count
		else _("Failed to send push notification to all registered devices."),
	}
