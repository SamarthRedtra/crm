from __future__ import annotations

import frappe


_patched = False
_original_handle = None


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

