from __future__ import annotations

import random
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from . import utils

CHALLENGE_CACHE_KEY = "agency_signup_challenge::{challenge_id}"
IDEMPOTENCY_CACHE_KEY = "agency_signup_idempotency::{key}"


def _parse_payload(data: str | dict[str, Any] | None = None) -> dict[str, Any]:
	if data is None:
		return utils.get_request_json(["full_name", "email", "password", "agency_name"])
	if isinstance(data, dict):
		return data
	return frappe.parse_json(data) or {}


def _next_temp_dfd_registration_id() -> str:
	while True:
		candidate = f"TMP-{frappe.generate_hash(length=10).upper()}"
		if not frappe.db.exists("Agent", {"dfd_registration_id": candidate}):
			return candidate


def _first_user_with_role(role: str) -> str | None:
	row = frappe.db.get_value(
		"Has Role",
		{"role": role, "parenttype": "User"},
		"parent",
		order_by="creation asc",
	)
	return row


def _create_verification_todo(agency_name: str, submitted_by: str):
	allocated_to = _first_user_with_role("System Manager") or _first_user_with_role("Sales Manager") or "Administrator"
	try:
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": allocated_to,
				"description": _(
					"Review newly registered agency {0} submitted by {1}."
				).format(agency_name, submitted_by),
				"reference_type": "Agency",
				"reference_name": agency_name,
				"priority": "High",
				"status": "Open",
			}
		)
		todo.flags.ignore_permissions = True
		todo.insert()
	except Exception:
		# Registration should not fail if the verification task cannot be created.
		frappe.log_error(frappe.get_traceback(), "Agency verification ToDo creation failed")


def _set_if_has_field(doc, fieldname: str, value):
	if fieldname in doc.meta.get_valid_columns():
		doc.set(fieldname, value)


def _challenge_key(challenge_id: str) -> str:
	return CHALLENGE_CACHE_KEY.format(challenge_id=challenge_id)


def _idempotency_key(raw_key: str) -> str:
	return IDEMPOTENCY_CACHE_KEY.format(key=raw_key.strip())


def _validate_challenge(payload: dict[str, Any]):
	challenge_id = (payload.get("challenge_id") or "").strip()
	challenge_answer = (payload.get("challenge_answer") or "").strip()

	if not challenge_id or not challenge_answer:
		frappe.throw(_("Captcha challenge is required."), frappe.ValidationError)

	expected_answer = frappe.cache().get_value(_challenge_key(challenge_id))
	if not expected_answer or str(expected_answer).strip() != challenge_answer:
		frappe.throw(_("Captcha validation failed. Please retry registration."), frappe.ValidationError)

	frappe.cache().delete_value(_challenge_key(challenge_id))


def _create_agency_comment(agency_name: str, content: str):
	try:
		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Agency",
				"reference_name": agency_name,
				"content": content,
			}
		)
		comment.flags.ignore_permissions = True
		comment.insert()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Agency audit comment creation failed")


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60 * 60)
def get_registration_challenge() -> dict[str, str]:
	left = random.randint(1, 9)
	right = random.randint(1, 9)
	challenge_id = frappe.generate_hash(length=16)
	frappe.cache().set_value(
		_challenge_key(challenge_id),
		str(left + right),
		expires_in_sec=5 * 60,
	)
	return {
		"challenge_id": challenge_id,
		"prompt": _("What is {0} + {1}?").format(left, right),
	}


@frappe.whitelist(methods=["POST"], allow_guest=True)
@rate_limit(limit=25, seconds=60 * 60, methods=["POST"])
def register_agency_admin(data: str | dict[str, Any] | None = None) -> dict[str, Any]:
	payload = _parse_payload(data)

	idempotency_key = (payload.get("idempotency_key") or "").strip()
	if idempotency_key:
		cached_result = frappe.cache().get_value(_idempotency_key(idempotency_key))
		if cached_result:
			return frappe.parse_json(cached_result)

	_validate_challenge(payload)

	full_name = (payload.get("full_name") or "").strip()
	email = (payload.get("email") or "").strip().lower()
	password = payload.get("password") or ""
	agency_name = (payload.get("agency_name") or "").strip()

	if not full_name or not email or not password or not agency_name:
		frappe.throw(_("Full name, email, password, and agency name are required."), frappe.ValidationError)
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters long."), frappe.ValidationError)

	if frappe.db.exists("User", email):
		frappe.throw(_("Email {0} is already registered.").format(email), frappe.DuplicateEntryError)
	if frappe.db.exists("Agency", {"agency_name": agency_name}):
		frappe.throw(_("Agency {0} already exists.").format(agency_name), frappe.DuplicateEntryError)

	user_doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"enabled": 1,
			"send_welcome_email": 0,
			"mobile_no": payload.get("phone"),
		}
	)
	user_doc.flags.ignore_permissions = True
	user_doc.flags.no_welcome_mail = True
	user_doc.new_password = password
	user_doc.insert()

	utils.ensure_agent_role(user_doc.name)

	agency_doc = frappe.get_doc(
		{
			"doctype": "Agency",
			"agency_name": agency_name,
			"status": "Active",
			"email": payload.get("agency_email") or email,
			"phone": payload.get("agency_phone") or payload.get("phone"),
			"website": payload.get("website"),
			"brn_id": payload.get("brn_id"),
			"billing_contact_name": payload.get("billing_contact_name") or full_name,
			"billing_email": payload.get("billing_email") or email,
			"onboarding_status": "Not Started",
			"billing_status": "Not Configured",
		}
	)
	_set_if_has_field(agency_doc, "verification_status", "Pending Verification")
	_set_if_has_field(agency_doc, "verification_notes", "")
	_set_if_has_field(agency_doc, "trial_status", "Not Started")
	_set_if_has_field(agency_doc, "is_on_trial", 0)
	agency_doc.flags.ignore_permissions = True
	agency_doc.insert()

	agent_doc = frappe.get_doc(
		{
			"doctype": "Agent",
			"user": user_doc.name,
			"agency": agency_doc.name,
			"agency_role": "Admin",
			"status": "Draft",
			"phone": payload.get("phone"),
			"whatsapp_number": payload.get("phone"),
			"dfd_registration_id": _next_temp_dfd_registration_id(),
			"billable": 1,
		}
	)
	agent_doc.flags.ignore_permissions = True
	agent_doc.insert()

	_create_verification_todo(agency_doc.name, user_doc.name)
	_create_agency_comment(
		agency_doc.name,
		_("Agency self-registration submitted by {0}. Verification status set to Pending Verification.").format(user_doc.name),
	)
	frappe.response.http_status_code = 201

	response = {
		"ok": True,
		"message": _("Agency registration submitted successfully."),
		"user": user_doc.name,
		"agency": agency_doc.name,
		"agent": agent_doc.name,
		"verification_status": getattr(agency_doc, "verification_status", "Pending Verification"),
		"next_step": "agency_verification",
	}
	if idempotency_key:
		frappe.cache().set_value(_idempotency_key(idempotency_key), frappe.as_json(response), expires_in_sec=60 * 60)
	return response
