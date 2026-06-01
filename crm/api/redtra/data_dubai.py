from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import frappe
import requests
from frappe import _
from frappe.integrations.utils import create_request_log
from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime, today


TOKEN_CACHE_KEY = "data_dubai::access_token"
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_PAGE_SIZE = 25
STATUS_NOT_CHECKED = "Not Checked"
STATUS_VERIFIED = "Verified"
STATUS_MISMATCH = "Mismatch"
STATUS_EXPIRED = "Expired"
STATUS_FAILED = "Failed"
AGENCY_MATCH_UNKNOWN = "Unknown"
AGENCY_MATCH_MATCHED = "Matched"
AGENCY_MATCH_MISMATCH = "Mismatch"

BROKER_IDENTIFIER_COLUMNS = {
	"brn_id": [
		"brn_id",
		"brn",
		"brn_no",
		"brn_number",
		"license_number",
		"broker_license_number",
		"card_number",
	],
	"dfd_registration_id": [
		"dfd_registration_id",
		"dld_registration_id",
		"registration_id",
		"registration_number",
		"broker_registration_number",
		"broker_number",
		"permit_number",
		"rera_id",
	],
}

REAL_ESTATE_IDENTIFIER_COLUMNS = {
	"company_license_number": [
		"company_license_number",
		"license_number",
		"trade_license_number",
		"real_estate_license_number",
		"license_no",
	],
	"rera_id": [
		"rera_id",
		"rera_number",
		"registration_number",
		"registration_id",
	],
	"brn_id": [
		"brn_id",
		"brn",
		"brn_no",
		"brn_number",
	],
}

BROKER_AGENCY_NAME_FIELDS = [
	"agency_name_en",
	"agency_name",
	"company_name_en",
	"company_name",
	"office_name_en",
	"office_name",
	"trade_name_en",
	"trade_name",
]
BROKER_EXPIRY_FIELDS = [
	"license_expiry_date",
	"expiry_date",
	"expiration_date",
	"license_end_date",
	"end_date",
	"broker_license_expiry_date",
]
REAL_ESTATE_AGENCY_NAME_FIELDS = [
	"agency_name_en",
	"agency_name",
	"company_name_en",
	"company_name",
	"trade_name_en",
	"trade_name",
	"licensee_name_en",
	"licensee_name",
]
REAL_ESTATE_EXPIRY_FIELDS = [
	"license_expiry_date",
	"expiry_date",
	"expiration_date",
	"license_end_date",
	"end_date",
	"real_estate_license_expiry_date",
]


@dataclass
class DDAConfig:
	base_url: str
	security_identifier: str
	client_id: str
	client_secret: str
	entity: str
	broker_dataset_name: str
	real_estate_dataset_name: str
	timeout_seconds: int


def is_configured() -> bool:
	try:
		get_config()
	except Exception:
		return False
	return True


def get_config() -> DDAConfig:
	settings = frappe.get_cached_doc("FCRM Settings", "FCRM Settings")
	base_url = (getattr(settings, "dda_base_url", None) or "").strip().rstrip("/")
	security_identifier = (getattr(settings, "dda_security_identifier", None) or "").strip()
	client_id = (getattr(settings, "dda_client_id", None) or "").strip()
	client_secret = (settings.get_password("dda_client_secret") or "").strip()
	entity = (getattr(settings, "dda_entity", None) or "").strip()
	broker_dataset_name = (getattr(settings, "dda_broker_dataset_name", None) or "").strip()
	real_estate_dataset_name = (getattr(settings, "dda_real_estate_dataset_name", None) or "").strip()
	timeout_seconds = max(5, cint(getattr(settings, "dda_request_timeout_seconds", None) or DEFAULT_TIMEOUT_SECONDS))

	if not base_url:
		frappe.throw(_("Data Dubai Base URL is not configured in FCRM Settings."))
	if not security_identifier:
		frappe.throw(_("Data Dubai Security Identifier is not configured in FCRM Settings."))
	if not client_id:
		frappe.throw(_("Data Dubai Client ID is not configured in FCRM Settings."))
	if not client_secret:
		frappe.throw(_("Data Dubai Client Secret is not configured in FCRM Settings."))
	if not entity:
		frappe.throw(_("Data Dubai Entity is not configured in FCRM Settings."))
	if not broker_dataset_name:
		frappe.throw(_("Data Dubai Broker Dataset Name is not configured in FCRM Settings."))
	if not real_estate_dataset_name:
		frappe.throw(_("Data Dubai Real Estate Dataset Name is not configured in FCRM Settings."))

	return DDAConfig(
		base_url=base_url,
		security_identifier=security_identifier,
		client_id=client_id,
		client_secret=client_secret,
		entity=entity,
		broker_dataset_name=broker_dataset_name,
		real_estate_dataset_name=real_estate_dataset_name,
		timeout_seconds=timeout_seconds,
	)


def verify_real_estate_license(
	*,
	agency_name: str,
	company_license_number: str | None = None,
	rera_id: str | None = None,
	brn_id: str | None = None,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict[str, Any]:
	config = get_config()
	record, raw_response = _query_dataset_record(
		config=config,
		dataset_name=config.real_estate_dataset_name,
		semantic_identifiers={
			"company_license_number": company_license_number,
			"rera_id": rera_id,
			"brn_id": brn_id,
		},
		request_description="DDA Real Estate License Verification",
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
	)
	verified_name = _extract_first(record, REAL_ESTATE_AGENCY_NAME_FIELDS)
	expiry_date = _extract_date(record, REAL_ESTATE_EXPIRY_FIELDS)
	agency_match_status = _compare_names(agency_name, verified_name)
	status = STATUS_FAILED
	notes = _("No matching real estate license record was found in Data Dubai.")

	if record:
		status = STATUS_VERIFIED
		notes = _("Real estate license verified from Data Dubai.")
		if expiry_date and getdate(expiry_date) < getdate(today()):
			status = STATUS_EXPIRED
			notes = _("The real estate license is expired in Data Dubai.")
		elif agency_match_status == AGENCY_MATCH_MISMATCH:
			status = STATUS_MISMATCH
			notes = _("Agency name does not match the Data Dubai record.")

	return {
		"status": status,
		"verified": status == STATUS_VERIFIED,
		"expiry_date": expiry_date,
		"verified_agency_name": verified_name,
		"agency_match_status": agency_match_status,
		"checked_on": str(now_datetime()),
		"notes": notes,
		"record": record,
		"payload": _safe_json_dumps({"record": record, "response": raw_response}),
	}


def verify_broker_license(
	*,
	agent_name: str | None = None,
	brn_id: str | None = None,
	dfd_registration_id: str | None = None,
	agency_name: str | None = None,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict[str, Any]:
	config = get_config()
	record, raw_response = _query_dataset_record(
		config=config,
		dataset_name=config.broker_dataset_name,
		semantic_identifiers={
			"brn_id": brn_id,
			"dfd_registration_id": dfd_registration_id,
		},
		request_description="DDA Broker License Verification",
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
	)
	verified_agency_name = _extract_first(record, BROKER_AGENCY_NAME_FIELDS)
	expiry_date = _extract_date(record, BROKER_EXPIRY_FIELDS)
	agency_match_status = _compare_names(agency_name, verified_agency_name)
	status = STATUS_FAILED
	notes = _("No matching broker license record was found in Data Dubai.")

	if record:
		status = STATUS_VERIFIED
		notes = _("Broker license verified from Data Dubai.")
		if expiry_date and getdate(expiry_date) < getdate(today()):
			status = STATUS_EXPIRED
			notes = _("The broker license is expired in Data Dubai.")
		elif agency_name and agency_match_status == AGENCY_MATCH_MISMATCH:
			status = STATUS_MISMATCH
			notes = _("The broker does not belong to the selected agency in Data Dubai.")

	return {
		"status": status,
		"verified": status == STATUS_VERIFIED,
		"expiry_date": expiry_date,
		"verified_agency_name": verified_agency_name,
		"agency_match_status": agency_match_status,
		"checked_on": str(now_datetime()),
		"notes": notes,
		"record": record,
		"agent_name": agent_name,
		"payload": _safe_json_dumps({"record": record, "response": raw_response}),
	}


def apply_agency_verification(doc, verification: dict[str, Any]) -> None:
	if not verification:
		return
	if hasattr(doc, "dda_real_estate_license_status"):
		doc.dda_real_estate_license_status = verification.get("status") or STATUS_NOT_CHECKED
	if hasattr(doc, "dda_real_estate_license_verified"):
		doc.dda_real_estate_license_verified = 1 if verification.get("verified") else 0
	if hasattr(doc, "dda_real_estate_license_expiry_date"):
		doc.dda_real_estate_license_expiry_date = verification.get("expiry_date")
	if hasattr(doc, "dda_verification_checked_on"):
		doc.dda_verification_checked_on = verification.get("checked_on")
	if hasattr(doc, "dda_verification_notes"):
		doc.dda_verification_notes = verification.get("notes")
	if hasattr(doc, "dda_verification_payload"):
		doc.dda_verification_payload = verification.get("payload")
	if hasattr(doc, "dda_verified_agency_name"):
		doc.dda_verified_agency_name = verification.get("verified_agency_name")
	if verification.get("verified_agency_name"):
		doc.agency_name = verification.get("verified_agency_name")


def apply_agent_verification(doc, verification: dict[str, Any]) -> None:
	if not verification:
		return
	if hasattr(doc, "dda_broker_license_status"):
		doc.dda_broker_license_status = verification.get("status") or STATUS_NOT_CHECKED
	if hasattr(doc, "dda_broker_license_verified"):
		doc.dda_broker_license_verified = 1 if verification.get("verified") else 0
	if hasattr(doc, "dda_broker_license_expiry_date"):
		doc.dda_broker_license_expiry_date = verification.get("expiry_date")
	if hasattr(doc, "dda_verification_checked_on"):
		doc.dda_verification_checked_on = verification.get("checked_on")
	if hasattr(doc, "dda_verification_notes"):
		doc.dda_verification_notes = verification.get("notes")
	if hasattr(doc, "dda_verification_payload"):
		doc.dda_verification_payload = verification.get("payload")
	if hasattr(doc, "dda_verified_agency_name"):
		doc.dda_verified_agency_name = verification.get("verified_agency_name")
	if hasattr(doc, "dda_agency_match_status"):
		doc.dda_agency_match_status = verification.get("agency_match_status") or AGENCY_MATCH_UNKNOWN


def build_agency_access_flags(agency_doc) -> dict[str, Any]:
	status = getattr(agency_doc, "dda_real_estate_license_status", STATUS_NOT_CHECKED) if agency_doc else STATUS_NOT_CHECKED
	expiry_date = getattr(agency_doc, "dda_real_estate_license_expiry_date", None) if agency_doc else None
	if status == STATUS_VERIFIED and expiry_date and getdate(expiry_date) < getdate(today()):
		status = STATUS_EXPIRED
	return {
		"agency_license_status": status,
		"agency_license_expiry_date": expiry_date,
		"requires_agency_license_verification": bool(agency_doc and status != STATUS_VERIFIED),
		"agency_verification_checked_on": getattr(agency_doc, "dda_verification_checked_on", None) if agency_doc else None,
		"agency_verification_notes": getattr(agency_doc, "dda_verification_notes", None) if agency_doc else None,
		"verified_agency_name": getattr(agency_doc, "dda_verified_agency_name", None) if agency_doc else None,
	}


def build_agent_access_flags(agent_doc_or_dict) -> dict[str, Any]:
	if not agent_doc_or_dict:
		return {
			"agent_license_status": STATUS_NOT_CHECKED,
			"agent_license_expiry_date": None,
			"requires_agent_license_verification": False,
			"agent_agency_match_status": AGENCY_MATCH_UNKNOWN,
			"agent_verification_checked_on": None,
			"agent_verification_notes": None,
			"verified_agency_name": None,
		}
	status = _get_value(agent_doc_or_dict, "dda_broker_license_status") or STATUS_NOT_CHECKED
	expiry_date = _get_value(agent_doc_or_dict, "dda_broker_license_expiry_date")
	if status == STATUS_VERIFIED and expiry_date and getdate(expiry_date) < getdate(today()):
		status = STATUS_EXPIRED
	agency_match_status = _get_value(agent_doc_or_dict, "dda_agency_match_status") or AGENCY_MATCH_UNKNOWN
	return {
		"agent_license_status": status,
		"agent_license_expiry_date": expiry_date,
		"requires_agent_license_verification": status != STATUS_VERIFIED or agency_match_status == AGENCY_MATCH_MISMATCH,
		"agent_agency_match_status": agency_match_status,
		"agent_verification_checked_on": _get_value(agent_doc_or_dict, "dda_verification_checked_on"),
		"agent_verification_notes": _get_value(agent_doc_or_dict, "dda_verification_notes"),
		"verified_agency_name": _get_value(agent_doc_or_dict, "dda_verified_agency_name"),
	}


def _query_dataset_record(
	*,
	config: DDAConfig,
	dataset_name: str,
	semantic_identifiers: dict[str, Any],
	request_description: str,
	reference_doctype: str | None,
	reference_docname: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
	for semantic_key, raw_value in semantic_identifiers.items():
		value = _clean_str(raw_value)
		if not value:
			continue
		candidate_columns = (
			BROKER_IDENTIFIER_COLUMNS.get(semantic_key)
			or REAL_ESTATE_IDENTIFIER_COLUMNS.get(semantic_key)
			or [semantic_key]
		)
		last_error = None
		for column in candidate_columns:
			try:
				response = _get_dataset_json(
					config=config,
					dataset_name=dataset_name,
					params={
						"page": 1,
						"pageSize": DEFAULT_PAGE_SIZE,
						"filter": f"{column}={value}",
					},
					request_description=request_description,
					reference_doctype=reference_doctype,
					reference_docname=reference_docname,
				)
			except Exception as exc:
				last_error = exc
				continue
			rows = _coerce_rows(response)
			match = _find_matching_row(rows, semantic_key=semantic_key, value=value)
			if match:
				return match, response
		if last_error:
			raise last_error
	return None, None


def _find_matching_row(rows: list[dict[str, Any]], *, semantic_key: str, value: str) -> dict[str, Any] | None:
	candidate_columns = (
		BROKER_IDENTIFIER_COLUMNS.get(semantic_key)
		or REAL_ESTATE_IDENTIFIER_COLUMNS.get(semantic_key)
		or [semantic_key]
	)
	needle = _normalize_text(value)
	for row in rows:
		for column in candidate_columns:
			row_value = _clean_str(row.get(column))
			if row_value and _normalize_text(row_value) == needle:
				return row
	return rows[0] if rows else None


def _coerce_rows(response: dict[str, Any] | None) -> list[dict[str, Any]]:
	if not isinstance(response, dict):
		return []
	rows = response.get("results") or response.get("result") or response.get("data") or []
	return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _get_dataset_json(
	*,
	config: DDAConfig,
	dataset_name: str,
	params: dict[str, Any],
	request_description: str,
	reference_doctype: str | None,
	reference_docname: str | None,
) -> dict[str, Any]:
	token = _get_access_token(config)
	base_url = f"{config.base_url}/secure/ddads/openapi/1.0.0/{config.entity}/{dataset_name}"
	query = {key: value for key, value in (params or {}).items() if value not in (None, "")}
	url = f"{base_url}?{urlencode(query)}" if query else base_url
	headers = {"Authorization": f"Bearer {token}"}
	integration_request = create_request_log(
		data={"method": "GET", "url": url, "params": query},
		service_name="Data Dubai",
		request_headers=_mask_headers(headers),
		url=url,
		is_remote_request=1,
		request_description=request_description,
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
		status="Queued",
	)
	response = None
	try:
		response = requests.get(url, headers=headers, timeout=config.timeout_seconds)
		response.raise_for_status()
	except requests.RequestException as exc:
		failure_payload = {
			"error": str(exc),
			"exception": exc.__class__.__name__,
			"params": query,
		}
		if response is not None:
			failure_payload["status_code"] = response.status_code
			failure_payload["body"] = (response.text or "")[:5000]
		integration_request.handle_failure(failure_payload)
		frappe.throw(_("Unable to reach Data Dubai services. Please try again later."))
	try:
		data = response.json()
	except ValueError:
		integration_request.handle_failure({"error": "invalid_json", "body": (response.text or "")[:5000]})
		frappe.throw(_("Invalid response received from Data Dubai services."))
	if not isinstance(data, dict):
		integration_request.handle_failure({"error": "unexpected_format", "type": type(data).__name__})
		frappe.throw(_("Unexpected Data Dubai response format."))
	integration_request.handle_success(data)
	return data


def _get_access_token(config: DDAConfig) -> str:
	cached = frappe.cache().get_value(TOKEN_CACHE_KEY)
	if cached:
		try:
			cached_data = frappe.parse_json(cached) or {}
			expires_at = cached_data.get("expires_at")
			if cached_data.get("access_token") and expires_at and get_datetime(expires_at) > now_datetime():
				return cached_data["access_token"]
		except Exception:
			pass

	url = f"{config.base_url}/secure/ssis/dubaiai/gatewaytoken/1.0.0/getAccessToken"
	headers = {
		"Content-Type": "application/json",
		"x-DDA-SecurityApplicationIdentifier": config.security_identifier,
	}
	payload = {
		"grant_type": "client_credentials",
		"client_id": config.client_id,
		"client_secret": config.client_secret,
	}
	integration_request = create_request_log(
		data={"method": "POST", "url": url, "payload": {"grant_type": "client_credentials", "client_id": config.client_id}},
		service_name="Data Dubai",
		request_headers=_mask_headers(headers),
		url=url,
		is_remote_request=1,
		request_description="DDA Access Token",
		status="Queued",
	)
	response = None
	try:
		response = requests.post(url, json=payload, headers=headers, timeout=config.timeout_seconds)
		response.raise_for_status()
	except requests.RequestException as exc:
		failure_payload = {
			"error": str(exc),
			"exception": exc.__class__.__name__,
		}
		if response is not None:
			failure_payload["status_code"] = response.status_code
			failure_payload["body"] = (response.text or "")[:5000]
		integration_request.handle_failure(failure_payload)
		frappe.throw(_("Unable to authenticate with Data Dubai services."))

	try:
		data = response.json()
	except ValueError:
		integration_request.handle_failure({"error": "invalid_json", "body": (response.text or "")[:5000]})
		frappe.throw(_("Invalid Data Dubai token response."))

	access_token = (data.get("access_token") or "").strip()
	expires_in = max(cint(data.get("expires_in") or 0), 60)
	if not access_token:
		integration_request.handle_failure({"error": "missing_access_token", "body": data})
		frappe.throw(_("Data Dubai access token was not returned."))

	integration_request.handle_success({"token_type": data.get("token_type"), "expires_in": expires_in})
	frappe.cache().set_value(
		TOKEN_CACHE_KEY,
		frappe.as_json(
			{
				"access_token": access_token,
				"expires_at": add_to_date(now_datetime(), seconds=expires_in - 60, as_string=True),
			}
		),
		expires_in_sec=max(expires_in - 60, 60),
	)
	return access_token


def _mask_headers(headers: dict[str, str]) -> dict[str, str]:
	masked: dict[str, str] = {}
	for key, value in (headers or {}).items():
		key_lower = key.lower()
		if key_lower in {"authorization", "x-dda-securityapplicationidentifier"}:
			masked[key] = "***"
		else:
			masked[key] = value
	return masked


def _extract_first(record: dict[str, Any] | None, fields: list[str]) -> str | None:
	if not record:
		return None
	for fieldname in fields:
		value = _clean_str(record.get(fieldname))
		if value:
			return value
	return None


def _extract_date(record: dict[str, Any] | None, fields: list[str]) -> str | None:
	if not record:
		return None
	for fieldname in fields:
		value = _clean_str(record.get(fieldname))
		if not value:
			continue
		try:
			return str(getdate(value))
		except Exception:
			continue
	return None


def _compare_names(left: str | None, right: str | None) -> str:
	if not _clean_str(left) or not _clean_str(right):
		return AGENCY_MATCH_UNKNOWN
	return AGENCY_MATCH_MATCHED if _normalize_text(left) == _normalize_text(right) else AGENCY_MATCH_MISMATCH


def _normalize_text(value: Any) -> str:
	text = _clean_str(value) or ""
	return "".join(ch for ch in text.lower() if ch.isalnum())


def _clean_str(value: Any) -> str | None:
	if value is None:
		return None
	text = str(value).strip()
	return text or None


def _safe_json_dumps(value: Any) -> str:
	try:
		return json.dumps(value, ensure_ascii=True, default=str)
	except Exception:
		return "{}"


def _get_value(doc_or_dict, fieldname: str):
	if isinstance(doc_or_dict, dict):
		return doc_or_dict.get(fieldname)
	return getattr(doc_or_dict, fieldname, None)
