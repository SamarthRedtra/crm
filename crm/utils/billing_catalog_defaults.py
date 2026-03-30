# Copyright (c) 2026, Redtra and contributors
"""Idempotent dummy rows for Agent Level (single) and Billing Addons (catalog)."""

from __future__ import annotations

import frappe


def _resolve_currency() -> str:
	c = frappe.db.get_single_value("Agency Billing Settings", "default_currency")
	if c and frappe.db.exists("Currency", c):
		return c
	if frappe.db.exists("Currency", "USD"):
		return "USD"
	first = frappe.get_all("Currency", pluck="name", limit=1)
	return first[0] if first else "USD"


def ensure_dummy_billing_catalog() -> None:
	"""Create sample Agent Level + Billing Addons when missing (safe to call repeatedly).

	Called from install hooks and patches only (not a public API).
	"""
	currency = _resolve_currency()

	if not frappe.db.count("Agent Level"):
		frappe.get_doc(
			{
				"doctype": "Agent Level",
				"level_name": "Standard Agent",
				"daily_rate": 99.0,
				"currency": currency,
				"active": 1,
				"sort_order": 0,
				"description": "Sample base per-agent daily rate. Edit or replace in Desk.",
			}
		).insert(ignore_permissions=True)

	addons = [
		{
			"addon_name": "Featured Listings",
			"pricing_model": "Daily Fixed",
			"rate": 25.0,
			"unit_label": "per listing / day",
			"sort_order": 10,
			"description": "Boost visibility for selected properties.",
		},
		{
			"addon_name": "Priority Support",
			"pricing_model": "Monthly Fixed",
			"rate": 199.0,
			"unit_label": None,
			"sort_order": 20,
			"description": "Faster response SLA for your agency.",
		},
		{
			"addon_name": "API Usage Pack",
			"pricing_model": "Usage Based",
			"rate": 0.5,
			"unit_label": "per 1k calls",
			"sort_order": 30,
			"description": "Metered API usage beyond included quota.",
		},
	]

	for row in addons:
		if frappe.db.exists("Billing Addon", row["addon_name"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Billing Addon",
				**row,
				"currency": currency,
				"active": 1,
			}
		).insert(ignore_permissions=True)
