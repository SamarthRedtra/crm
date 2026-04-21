import os

import frappe
from frappe.modules.import_file import import_file_by_path


def execute():
	"""Re-import billing-related workspaces/sidebars so desk links match app JSON."""
	base = frappe.get_app_path("crm")
	paths = [
		os.path.join(base, "fcrm", "workspace", "property_management", "property_management.json"),
		os.path.join(base, "fcrm", "workspace", "frappe_crm", "frappe_crm.json"),
		os.path.join(base, "workspace_sidebar", "property_management.json"),
		os.path.join(base, "workspace_sidebar", "redtra_crm.json"),
	]
	for path in paths:
		if os.path.isfile(path):
			import_file_by_path(path, force=True, ignore_version=True)
