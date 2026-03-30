"""Manual verification helper for billing catalog policy.

Run from bench root:

  bench --site <your_site> execute crm.bench_scripts.verify_billing_catalog.execute

Checks Agent Level row count (singleton), and prints ``public_billing_preview`` base rate + add-on count.
"""

from __future__ import annotations

import frappe

from crm.api.redtra import billing


def execute():
	level_count = frappe.db.count("Agent Level")
	preview = billing.public_billing_preview()
	al = preview.get("agent_level")
	addons = preview.get("billing_addons") or []

	print("--- verify_billing_catalog ---")
	print(f"Agent Level rows: {level_count}")
	print(f"agent_level: {al}")
	print(f"billing_addons count: {len(addons)}")
	if level_count > 1:
		print(
			"WARNING: Multiple Agent Level rows; run `bench migrate` so patch "
			"`consolidate_agent_levels_to_one` can merge them.",
		)
