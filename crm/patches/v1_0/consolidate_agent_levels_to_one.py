import frappe


def execute():
	"""Keep a single Agent Level (lowest sort_order, then name). Re-point agents and remove extras."""
	levels = frappe.get_all("Agent Level", pluck="name", order_by="sort_order asc, level_name asc")
	if len(levels) <= 1:
		return

	keeper = levels[0]
	for name in levels[1:]:
		frappe.db.sql(
			"UPDATE `tabAgent` SET `agent_level` = %s WHERE `agent_level` = %s",
			(keeper, name),
		)
		frappe.delete_doc("Agent Level", name, ignore_permissions=True, force=True)

	frappe.db.commit()
