import frappe


def execute():
	"""Migrate transaction_type from 'Rent' to 'Rented' in Property Transaction Log."""
	frappe.db.sql(
		"""
		UPDATE `tabProperty Transaction Log`
		SET transaction_type = 'Rented'
		WHERE transaction_type = 'Rent'
		"""
	)
	frappe.db.commit()
