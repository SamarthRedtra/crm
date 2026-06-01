from __future__ import annotations

import random
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from . import utils
from .auth import _ensure_agency_user_permission

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
	brn_id = (payload.get("brn_id") or "").strip()
	rera_id = (payload.get("rera_id") or "").strip()

	if not full_name or not email or not password or not agency_name:
		frappe.throw(_("Full name, email, password, and agency name are required."), frappe.ValidationError)
	if not brn_id or not rera_id:
		frappe.throw(_("BRN/BLN ID and RERA ID are required."), frappe.ValidationError)
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
			"roles": [{"role": r} for r in utils.get_agency_member_roles("Admin")],
		}
	)
	user_doc.flags.ignore_permissions = True
	user_doc.flags.no_welcome_mail = True
	user_doc.new_password = password
	user_doc.insert()

	utils.ensure_agency_member_crm_roles(user_doc.name, "Admin")

	agency_doc = frappe.get_doc(
		{
			"doctype": "Agency",
			"agency_name": agency_name,
			"status": "Active",
			"email": payload.get("agency_email") or email,
			"phone": payload.get("agency_phone") or payload.get("phone"),
			"website": payload.get("website"),
			"brn_id": brn_id,
			"rera_id": rera_id,
			"company_license_number": payload.get("company_license_number"),
			"whatsapp_number": payload.get("agency_phone") or payload.get("phone"),
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
	_try_verify_registered_agency(agency_doc)
	_try_create_stripe_customer_for_agency(agency_doc)

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

	_ensure_agency_user_permission(user_doc.name, agency_doc.name)

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


def _try_create_stripe_customer_for_agency(agency_doc):
	"""Best-effort Stripe customer provisioning during agency signup.

	Signup must not fail if Stripe is unavailable or not configured.
	"""
	try:
		from . import billing

		if not billing._is_billing_enabled():
			return
		if not billing._stripe_enabled():
			return
		billing._ensure_stripe_customer(agency_doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Stripe customer provisioning failed for agency {agency_doc.name}",
		)


def _try_verify_registered_agency(agency_doc):
	"""Best-effort DDA verification for self-registered agencies.

	This should not block account creation because login is soft-allow, but it should
	persist the expiry date and normalize the agency name whenever DDA confirms it.
	"""
	try:
		from . import data_dubai

		if not data_dubai.is_configured():
			return

		verification = data_dubai.verify_real_estate_license(
			agency_name=agency_doc.agency_name,
			company_license_number=getattr(agency_doc, "company_license_number", None),
			rera_id=getattr(agency_doc, "rera_id", None),
			brn_id=getattr(agency_doc, "brn_id", None),
			reference_doctype="Agency",
			reference_docname=agency_doc.name,
		)
		verified_agency_name = verification.get("verified_agency_name")
		if verified_agency_name:
			existing_agency = frappe.db.get_value("Agency", {"agency_name": verified_agency_name}, "name")
			if existing_agency and existing_agency != agency_doc.name:
				verification["notes"] = _(
					"{0} Existing agency {1} already uses the verified Data Dubai name."
				).format(verification.get("notes") or "", existing_agency)
				verification["verified_agency_name"] = agency_doc.agency_name
		data_dubai.apply_agency_verification(agency_doc, verification)
		agency_doc.flags.ignore_permissions = True
		agency_doc.save()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Data Dubai verification failed for agency {agency_doc.name}",
		)


@frappe.whitelist()
def get_agent_onboarding_context() -> dict[str, Any]:
	"""Returns pre-fill data for agent onboarding from linked agency."""
	user = frappe.session.user
	agent = frappe.db.get_value(
		"Agent",
		{"user": user},
		["name", "agency", "phone", "whatsapp_number", "brn_id"],
		as_dict=True,
	)
	if not agent:
		return {}

	agency_data = {}
	if agent.agency:
		agency_data = frappe.db.get_value(
			"Agency",
			agent.agency,
			["phone", "whatsapp_number", "brn_id", "agency_name"],
			as_dict=True,
		)

	return {
		"agent": agent,
		"agency_defaults": {
			"phone": agency_data.get("phone") if not agent.phone else None,
			"whatsapp_number": agency_data.get("whatsapp_number") if not agent.whatsapp_number else None,
			"brn_id": agency_data.get("brn_id") if not agent.brn_id else None,
		},
	}
