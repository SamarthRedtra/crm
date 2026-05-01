import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Event": [
				{
					"fieldname": "appointment_customer",
					"label": "Appointment Customer",
					"fieldtype": "Link",
					"options": "Customer",
					"insert_after": "property",
				},
			],
		},
		ignore_validate=True,
	)
