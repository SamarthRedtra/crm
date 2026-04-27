from __future__ import annotations

import frappe


_patched = False
_original_handle = None
_make_form_dict_patched = False
_original_make_form_dict = None
_validate_auth_patched = False
_original_validate_auth = None
_upload_file_patched = False
_original_upload_file = None


def _patched_make_form_dict(request):
	"""Wrap make_form_dict to ensure sid from URL is in form_dict for /crm paths."""
	_original_make_form_dict(request)
	try:
		from crm.api.redtra.sid_handler import ensure_sid_in_form_dict
		ensure_sid_in_form_dict()
	except Exception:
		pass


def patch_make_form_dict_for_sid():
	"""Patch make_form_dict so sid from /crm?sid=xxx is preserved before Session creation."""
	global _make_form_dict_patched, _original_make_form_dict

	if _make_form_dict_patched:
		return

	import frappe.app as app_module

	_original_make_form_dict = app_module.make_form_dict
	app_module.make_form_dict = _patched_make_form_dict
	_make_form_dict_patched = True


def _rebuild_api_url_map():
	from werkzeug.routing import Map, Submount

	from frappe.api import ApiVersion
	from frappe.api.v1 import url_rules as v1_rules
	from frappe.api.v2 import url_rules as v2_rules

	frappe.api.API_URL_MAP = Map(
		[
			Submount("/api", v1_rules),
			Submount(f"/api/{ApiVersion.V1.value}", v1_rules),
			Submount(f"/api/{ApiVersion.V2.value}", v2_rules),
		],
		strict_slashes=False,
		merge_slashes=False,
	)


def _patched_handle(request):
	return _original_handle(request)


@frappe.whitelist()
def _patched_upload_file():
	"""Ensures total_file_size is at least 0 to prevent TypeError in Frappe handler."""
	if frappe.form_dict.get("total_file_size") is None:
		frappe.form_dict.total_file_size = 0
	
	if frappe.form_dict.get("total_chunks") is None:
		frappe.form_dict.total_chunks = 1
	
	if frappe.form_dict.get("current_chunk") is None:
		frappe.form_dict.current_chunk = 0

	return _original_upload_file()


def _patched_validate_auth():
	"""Frappe raises AuthenticationError if Authorization: Bearer x is sent but user is still Guest.

	Redtra sends JWTs in the same header; when the token is expired/invalid our hook leaves Guest.
	That must not block allow_guest API routes (e.g. POST /api/agents/.../reviews).
	"""
	authorization_header = frappe.get_request_header("Authorization", "").split(" ")

	if len(authorization_header) == 2:
		frappe.auth.validate_oauth(authorization_header)
		frappe.auth.validate_auth_via_api_keys(authorization_header)

	frappe.auth.validate_auth_via_hooks()

	if len(authorization_header) == 2 and frappe.session.user in ("", "Guest"):
		if getattr(frappe.local, "redtra_guest_after_stale_bearer", False):
			return
		raise frappe.AuthenticationError


def patch_validate_auth_for_redtra_bearer():
	global _validate_auth_patched, _original_validate_auth

	if _validate_auth_patched:
		return

	import frappe.auth as auth_module

	_original_validate_auth = auth_module.validate_auth
	auth_module.validate_auth = _patched_validate_auth
	_validate_auth_patched = True


def patch_upload_file():
	global _upload_file_patched, _original_upload_file

	if _upload_file_patched:
		return

	import frappe.handler as handler_module

	_original_upload_file = handler_module.upload_file
	handler_module.upload_file = _patched_upload_file
	_upload_file_patched = True


def patch_frappe_api_handler():
	global _patched, _original_handle

	if _patched:
		return

	_original_handle = frappe.api.handle
	_rebuild_api_url_map()
	frappe.api.handle = _patched_handle
	_patched = True
	patch_make_form_dict_for_sid()
	patch_validate_auth_for_redtra_bearer()
	patch_upload_file()

