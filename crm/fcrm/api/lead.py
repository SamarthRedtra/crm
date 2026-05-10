import frappe

from crm.api.lead_sync_api import sync_lead


@frappe.whitelist()
def create_lead_against_property(lead_data, property_name):
	"""Deprecated name — delegates to ``crm.api.lead_sync_api.sync_lead``."""
	return sync_lead(lead=lead_data, property_name=property_name)
