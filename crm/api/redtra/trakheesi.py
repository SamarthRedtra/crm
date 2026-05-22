from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import frappe
import requests
from frappe import _
from frappe.integrations.utils import create_request_log
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


def verify_listing(
	*,
	listing_number: str,
	license_number: str,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict[str, Any]:
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
		request_description="Trakheesi Listing Validation",
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
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
		"property_name_ar": property_data.get("propertyNameAr"),
		"building_name_en": property_data.get("buildingNameEn"),
		"building_name_en_fallback": property_data.get("buildlngNameEn"),
		"building_name_ar": property_data.get("buildingNameAr"),
		"permit_location": match.get("permitLocation"),
		"listing_type_en": property_data.get("permitTypeNameEn"),
		"property_type_en": property_data.get("propertyTypeNameEn"),
		"rooms_count": property_data.get("roomsCount"),
		"room_type_en": property_data.get("roomTypeEn"),
		"floor_number": property_data.get("floorNumber"),
		"facilities": property_data.get("facilities"),
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
	if not getattr(doc, "listing_type", None):
		mapped_listing_type = _map_listing_type(verification.get("listing_type_en"))
		if mapped_listing_type:
			doc.listing_type = mapped_listing_type
	if not getattr(doc, "bedrooms", None):
		bedrooms = _extract_bedrooms(verification)
		if bedrooms is not None:
			doc.bedrooms = bedrooms
	if not getattr(doc, "city", None) and verification.get("permit_location"):
		doc.city = verification.get("permit_location")
	if not getattr(doc, "address_line1", None):
		doc.address_line1 = (
			verification.get("building_name_en")
			or verification.get("building_name_en_fallback")
			or verification.get("property_name_en")
			or verification.get("building_name_ar")
			or verification.get("property_name_ar")
		)
	if not getattr(doc, "address_line2", None):
		floor_number = (verification.get("floor_number") or "").strip()
		if floor_number:
			doc.address_line2 = f"Floor {floor_number}"
	_sync_amenities_from_facilities(doc, verification.get("facilities"))


def _map_listing_type(listing_type: Any) -> str | None:
	value = (listing_type or "").strip().lower()
	if value == "rent":
		return "Rent"
	if value == "sale":
		return "Buy"
	return None


def _extract_bedrooms(verification: dict[str, Any]) -> int | None:
	rooms_count = str(verification.get("rooms_count") or "").strip()
	if rooms_count.isdigit():
		return cint(rooms_count)

	room_type = (verification.get("room_type_en") or "").strip()
	if room_type:
		match = next((part for part in room_type.split() if part.isdigit()), None)
		if match:
			return cint(match)
	return None


def _normalize_facility_name(facility: Any) -> str:
	if isinstance(facility, str):
		return facility.strip()
	if isinstance(facility, dict):
		for key in ("facilityNameEn", "facilityNameAr", "nameEn", "nameAr", "name", "label"):
			value = (facility.get(key) or "").strip()
			if value:
				return value
	return ""


def _sync_amenities_from_facilities(doc, facilities: Any) -> None:
	if not facilities or not hasattr(doc, "amenities"):
		return

	if not isinstance(facilities, list):
		facilities = [facilities]

	existing = {
		(row.amenity_name or "").strip()
		for row in (doc.amenities or [])
		if getattr(row, "amenity_name", None)
	}
	new_names = []
	for facility in facilities:
		name = _normalize_facility_name(facility)
		if name and name not in existing:
			new_names.append(name)
			existing.add(name)

	for amenity_name in new_names:
		if not frappe.db.exists("Amenity", amenity_name):
			frappe.get_doc({"doctype": "Amenity", "amenity_name": amenity_name}).insert(ignore_permissions=True)
		doc.append("amenities", {"amenity_name": amenity_name})


def fetch_delisted_listings(
	*,
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict[str, Any]:
	config = get_config()
	response = _get_json(
		url=config.delist_base_url,
		headers={"authorizationkey": config.authorization_key},
		timeout=config.timeout_seconds,
		request_description="Trakheesi Delisted Listings",
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
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


def _mask_request_headers(headers: dict[str, str]) -> dict[str, str]:
	return {
		key: ("***" if key.lower() == "authorizationkey" else value)
		for key, value in (headers or {}).items()
	}


def _get_json(
	*,
	url: str,
	headers: dict[str, str],
	timeout: int,
	request_description: str = "Trakheesi API",
	reference_doctype: str | None = None,
	reference_docname: str | None = None,
) -> dict[str, Any]:
	integration_request = create_request_log(
		data={"method": "GET", "url": url},
		service_name="Trakheesi",
		request_headers=_mask_request_headers(headers),
		url=url,
		is_remote_request=1,
		request_description=request_description,
		reference_doctype=reference_doctype,
		reference_docname=reference_docname,
		status="Queued",
	)

	response = None
	try:
		response = requests.get(url, headers=headers, timeout=timeout)
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
		frappe.log_error(
			title="Trakheesi API request failed",
			message=frappe.get_traceback(),
		)
		frappe.throw(_("Unable to reach Trakheesi services. Please try again later."))

	try:
		data = response.json()
	except ValueError:
		integration_request.handle_failure(
			{"error": "invalid_json", "body": (response.text or "")[:5000]}
		)
		frappe.log_error(
			title="Trakheesi API invalid JSON",
			message=response.text,
		)
		frappe.throw(_("Invalid response received from Trakheesi services."))

	if not isinstance(data, dict):
		integration_request.handle_failure(
			{"error": "unexpected_format", "type": type(data).__name__}
		)
		frappe.throw(_("Unexpected Trakheesi response format."))

	integration_request.handle_success(data)
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
