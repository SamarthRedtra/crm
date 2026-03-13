from __future__ import annotations

import frappe


_patched = False
_original_handle = None
_make_form_dict_patched = False
_original_make_form_dict = None


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


def patch_frappe_api_handler():
	global _patched, _original_handle

	if _patched:
		return

	_original_handle = frappe.api.handle
	_rebuild_api_url_map()
	frappe.api.handle = _patched_handle
	_patched = True
	patch_make_form_dict_for_sid()

