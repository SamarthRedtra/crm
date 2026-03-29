# Copyright (c) 2026, Redtra Technologies FZE LLC and Contributors
"""Redirect bare /property_management_setup to the Desk setup page."""

from urllib.parse import quote

import frappe

no_cache = 1

DESK_SETUP_PATH = "/desk/property_management_setup"


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.redirect(f"/login?redirect-to={quote(DESK_SETUP_PATH)}")
	frappe.redirect(DESK_SETUP_PATH)
