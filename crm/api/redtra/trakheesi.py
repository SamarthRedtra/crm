from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import frappe
import requests
from frappe import _
from frappe.utils import cint, now_datetime


ALLOWED_PERMIT_STATUS_IDS = {6, 7}
DELIST_COMMENT_PREFIX = "Trakheesi Delist Sync"


@dataclass
class TrakheesiConfig:
	validation_base_url: str
	delist_base_url: str
	authorization_key: str
	timeout_seconds: int


def get_config() -> TrakheesiConfig:
	settings = frappe.get_cached_doc("FCRM Settings", "FCRM Settings")
	validation_base_url = (settings.get("trakheesi_validation_base_url") or "").strip()
	delist_base_url = (settings.get("trakheesi_delist_base_url") or "").strip()
	authorization_key = (settings.get_password("trakheesi_authorization_key") or "").strip()
	timeout_seconds = cint(settings.get("trakheesi_request_timeout_seconds") or 15)
	timeout_seconds = max(5, timeout_seconds)

	if not validation_base_url:
		frappe.throw(_("Trakheesi Validation Base URL is not configured in FCRM Settings."))
	if not delist_base_url:
		frappe.throw(_("Trakheesi Delist Base URL is not configured in FCRM Settings."))
	if not authorization_key:
		frappe.throw(_("Trakheesi Authorization Key is not configured in FCRM Settings."))

	return TrakheesiConfig(
		validation_base_url=validation_base_url.rstrip("/"),
		delist_base_url=delist_base_url.rstrip("/"),
		authorization_key=authorization_key,
		timeout_seconds=timeout_seconds,
	)


def verify_listing(*, listing_number: str, license_number: str) -> dict[str, Any]:
	config = get_config()
	listing = (listing_number or "").strip()
	license_no = (license_number or "").strip()
	if not listing:
		frappe.throw(_("Trakheesi listing number is required."))
	if not license_no:
		frappe.throw(_("License number is required."))

	url = f"{config.validation_base_url}/{listing}/{license_no}"
	response = _get_json(
		url=url,
		headers={"authorizationkey": config.authorization_key},
		timeout=config.timeout_seconds,
	)
	result_rows = response.get("result") or []
	errors = response.get("errors") or []
	record_count = cint(response.get("recordCount") or 0)

	if errors or not result_rows or record_count <= 0:
		_raise_verification_error(response)

	match = _find_matching_row(result_rows, listing=listing, license_number=license_no)
	if not match:
		frappe.throw(_("Trakheesi verification mismatch for listing/license number."), frappe.ValidationError)

	permit_status_id = cint(match.get("permitStatusId") or 0)
	if permit_status_id not in ALLOWED_PERMIT_STATUS_IDS:
		frappe.throw(
			_("Trakheesi permit status {0} is not eligible for listing integration.").format(permit_status_id),
			frappe.ValidationError,
		)

	property_data = match.get("property") or {}
	verification_payload = {
		"full_response": response,
		"matched_result": match,
	}
	return {
		"listing_number": listing,
		"license_number": license_no,
		"listing_guid": match.get("listingGuid"),
		"validation_url": match.get("validationUrl"),
		"verified_at": str(now_datetime()),
		"property_size": property_data.get("propertySize"),
		"zone_name_en": property_data.get("zoneNameEn"),
		"property_name_en": property_data.get("propertyNameEn"),
		"building_name_en": property_data.get("buildingNameEn"),
		"permit_location": match.get("permitLocation"),
		"verification_payload": json.dumps(verification_payload, ensure_ascii=True),
	}


def apply_verification_to_property(doc, verification: dict[str, Any]) -> None:
	"""Persist Trakheesi verify_listing results on Property (canonical sync from API response)."""
	if not verification:
		return
	doc.trakheesi_listing_guid = verification.get("listing_guid")
	doc.trakheesi_validation_url = verification.get("validation_url")
	doc.trakheesi_last_verified_on = verification.get("verified_at")
	doc.trakheesi_verification_payload = verification.get("verification_payload")
	if verification.get("property_size") not in (None, ""):
		doc.area_sqft = verification.get("property_size")
	if verification.get("zone_name_en"):
		doc.zone_name = verification.get("zone_name_en")
	if not getattr(doc, "city", None) and verification.get("permit_location"):
		doc.city = verification.get("permit_location")
	if not getattr(doc, "address_line1", None):
		doc.address_line1 = verification.get("building_name_en") or verification.get("property_name_en")


def fetch_delisted_listings() -> dict[str, Any]:
	config = get_config()
	response = _get_json(
		url=config.delist_base_url,
		headers={"authorizationkey": config.authorization_key},
		timeout=config.timeout_seconds,
	)
	result_rows = response.get("result") or []
	if not isinstance(result_rows, list):
		result_rows = []

	return {
		"rows": result_rows,
		"record_count": cint(response.get("recordCount") or len(result_rows)),
		"errors": response.get("errors") or [],
		"raw_response": response,
		"fetched_at": str(now_datetime()),
	}


def build_delist_comment(*, row: dict[str, Any]) -> str:
	listing = (row.get("listingNumber") or "").strip()
	license_no = (row.get("LicenseNumber") or row.get("licenseNumber") or "").strip()
	delist_date = (row.get("delistDate") or "").strip()
	status_name = (row.get("statusNameEn") or row.get("statusNameAr") or "").strip()

	return (
		f"{DELIST_COMMENT_PREFIX}: listing={listing}, license={license_no}, "
		f"delist_date={delist_date}, status={status_name}"
	)


def is_duplicate_delist_comment(*, property_name: str, comment_content: str) -> bool:
	return bool(
		frappe.db.exists(
			"Comment",
			{
				"reference_doctype": "Property",
				"reference_name": property_name,
				"comment_type": "Comment",
				"content": comment_content,
			},
		)
	)


def _get_json(*, url: str, headers: dict[str, str], timeout: int) -> dict[str, Any]:
	try:
		response = requests.get(url, headers=headers, timeout=timeout)
		response.raise_for_status()
	except requests.RequestException:
		frappe.log_error(
			title="Trakheesi API request failed",
			message=frappe.get_traceback(),
		)
		frappe.throw(_("Unable to reach Trakheesi services. Please try again later."))

	try:
		data = response.json()
	except ValueError:
		frappe.log_error(
			title="Trakheesi API invalid JSON",
			message=response.text,
		)
		frappe.throw(_("Invalid response received from Trakheesi services."))

	if not isinstance(data, dict):
		frappe.throw(_("Unexpected Trakheesi response format."))
	return data


def _find_matching_row(rows: list[dict[str, Any]], *, listing: str, license_number: str) -> dict[str, Any] | None:
	for row in rows:
		row_listing = (row.get("listingNumber") or "").strip()
		row_license = (row.get("licenseNumber") or row.get("LicenseNumber") or "").strip()
		if row_listing == listing and row_license == license_number:
			return row
	return None


def _raise_verification_error(response: dict[str, Any]) -> None:
	errors = response.get("errors") or []
	message_en = None
	for error in errors:
		if isinstance(error, dict) and error.get("messageEn"):
			message_en = error.get("messageEn")
			break

	frappe.throw(
		_(message_en or "Trakheesi verification failed for this listing."),
		frappe.ValidationError,
	)
