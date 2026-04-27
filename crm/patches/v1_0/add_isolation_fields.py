import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	# Add custom fields to Contact
	create_custom_fields({
		"Contact": [
			{
				"fieldname": "agency",
				"label": "Agency",
				"fieldtype": "Link",
				"options": "Agency",
				"in_list_view": 1,
				"insert_after": "email_id"
			},
			{
				"fieldname": "created_by",
				"label": "Created By",
				"fieldtype": "Link",
				"options": "User",
				"in_list_view": 1,
				"insert_after": "agency"
			}
		]
	})
