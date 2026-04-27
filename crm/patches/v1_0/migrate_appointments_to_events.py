import frappe

def execute():
	appointments = frappe.get_all(
		"Property Appointment",
		filters={"status": "Scheduled"},
		fields=["name"]
	)
	
	for appt in appointments:
		doc = frappe.get_doc("Property Appointment", appt.name)
		try:
			doc.sync_to_event()
		except Exception:
			pass
