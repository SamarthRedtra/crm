import frappe

def execute():
	role = "Agency Manager"
	if not frappe.db.exists("Role", role):
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role,
			"desk_access": 1
		}).insert()
