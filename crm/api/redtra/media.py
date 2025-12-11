from __future__ import annotations

from typing import Any

import base64

import frappe
from frappe import _

from . import properties, utils

MAX_PROPERTY_IMAGES = 10


@frappe.whitelist(methods=["POST"])
@utils.require_jwt(roles={"Agent", "System Manager"})
def upload_property_image(property_id: str) -> dict[str, Any]:
	data = utils.get_request_json(["file_name", "filedata"])
	file_name = data["file_name"]
	filedata = _extract_base64(data["filedata"])

	prop_doc = frappe.get_doc("Property", property_id)
	properties._validate_property_owner(prop_doc)

	existing_files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Property",
			"attached_to_name": property_id,
			"is_folder": 0,
		},
		fields=["name"],
		ignore_permissions=True,
	)
	if len(existing_files) >= MAX_PROPERTY_IMAGES:
		frappe.throw(
			_("A property can have at most {0} images.").format(MAX_PROPERTY_IMAGES),
			exc=frappe.LimitExceededError,
		)

	file_doc = _create_file(
		file_name=file_name,
		filedata=filedata,
		attached_to_doctype="Property",
		attached_to_name=property_id,
		is_private=0,
	)

	if not prop_doc.primary_image:
		prop_doc.primary_image = file_doc.file_url
		prop_doc.save(ignore_permissions=True)

	frappe.local.response["http_status_code"] = 201
	return _serialize_file(file_doc)


@frappe.whitelist(methods=["POST"])
@utils.require_jwt()
def upload_profile_photo() -> dict[str, Any]:
	data = utils.get_request_json(["file_name", "filedata"])
	file_name = data["file_name"]
	filedata = _extract_base64(data["filedata"])

	user = utils.get_current_user()

	file_doc = _create_file(
		file_name=file_name,
		filedata=filedata,
		attached_to_doctype="User",
		attached_to_name=user,
		is_private=0,
	)

	user_doc = frappe.get_doc("User", user)
	user_doc.user_image = file_doc.file_url
	user_doc.save(ignore_permissions=True)

	agent_name = frappe.db.get_value("Agent", {"user": user})
	if agent_name:
		agent_doc = frappe.get_doc("Agent", agent_name)
		agent_doc.profile_image = file_doc.file_url
		agent_doc.save(ignore_permissions=True)

	frappe.local.response["http_status_code"] = 201
	return _serialize_file(file_doc)


def _create_file(
	*,
	file_name: str,
	filedata: str,
	attached_to_doctype: str,
	attached_to_name: str,
	is_private: int,
) -> Any:
	file_doc = frappe.get_doc(  # type: ignore[call-arg]
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": attached_to_doctype,
			"attached_to_name": attached_to_name,
			"content": filedata,
			"decode": 1,
			"is_private": is_private,
		}
	)
	file_doc.save(ignore_permissions=True)
	return file_doc


def _extract_base64(raw_data: str) -> str:
	if "," in raw_data:
		prefix, b64_data = raw_data.split(",", 1)
		if not prefix.lower().startswith("data:"):
			return raw_data
		return b64_data
	# validate base64
	try:
		base64.b64decode(raw_data, validate=True)
	except Exception as exc:
		frappe.throw(_("Invalid file data: {0}").format(exc))
	return raw_data


def _serialize_file(file_doc) -> dict[str, Any]:
	return {
		"id": file_doc.name,
		"file_name": file_doc.file_name,
		"file_url": file_doc.file_url,
		"is_private": bool(file_doc.is_private),
	}
