import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	custom_fields = {
		"Event": [
			{
				"fieldname": "sync_with_appointment",
				"label": "Sync with Appointment",
				"fieldtype": "Check",
				"insert_after": "event_type"
			},
			{
				"fieldname": "customer_email",
				"label": "Customer Email",
				"fieldtype": "Data",
				"insert_after": "sync_with_appointment"
			},
			{
				"fieldname": "property",
				"label": "Property",
				"fieldtype": "Link",
				"options": "Property",
				"insert_after": "customer_email"
			}
		]
	}
	create_custom_fields(custom_fields, ignore_validate=True)
