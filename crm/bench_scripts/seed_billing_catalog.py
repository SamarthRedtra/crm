"""Create dummy Agent Level + Billing Addons when missing (idempotent).

  bench --site <site> execute crm.bench_scripts.seed_billing_catalog.execute
"""

import frappe

from crm.utils.billing_catalog_defaults import ensure_dummy_billing_catalog


def execute():
	ensure_dummy_billing_catalog()
	frappe.db.commit()
