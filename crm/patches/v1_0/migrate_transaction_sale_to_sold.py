import frappe


def execute():
	"""Migrate transaction_type from 'Sale' to 'Sold' in Property Transaction Log."""
	frappe.db.sql(
		"""
		UPDATE `tabProperty Transaction Log`
		SET transaction_type = 'Sold'
		WHERE transaction_type = 'Sale'
		"""
	)
	frappe.db.commit()
