import frappe


def execute():
	from frappe.permissions import add_permission, update_permission_property

	roles = ("Agent", "Agency Manager")
	for role in roles:
		add_permission("Contact", role, 0)
		for perm in ("read", "create", "write", "select"):
			update_permission_property("Contact", role, 0, perm, 1)
