import frappe

from crm.utils.billing_catalog_defaults import ensure_dummy_billing_catalog


def execute():
	ensure_dummy_billing_catalog()
	frappe.db.commit()
