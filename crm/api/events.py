import frappe
from frappe import _

@frappe.whitelist()
def create_event_with_appointment(event_data, appointment_data=None):
	event = frappe.get_doc({
		"doctype": "Event",
		**event_data
	})
	event.insert()
	
	if appointment_data and appointment_data.get("sync"):
		# Create Property Appointment
		# Map Event fields to Appointment
		appointment = frappe.get_doc({
			"doctype": "Property Appointment",
			"property": appointment_data.get("property"),
			"customer": appointment_data.get("customer_email"), # Assuming email as customer for now or search/create lead
			"start_datetime": event.starts_on,
			"end_datetime": event.ends_on,
			"status": "Scheduled",
			"agent": frappe.db.get_value("Agent", {"user": frappe.session.user}, "name")
		})
		
		# Resolve customer (Link field)
		if appointment_data.get("customer_email"):
			# Check if contact exists
			contact = frappe.db.get_value("Contact", {"email_id": appointment_data.get("customer_email")}, "name")
			if not contact:
				# Create contact/lead if needed? For now let's assume valid contact or handle later
				pass
			appointment.customer = contact or appointment_data.get("customer_email")

		appointment.insert()
		
		# Link Event to Appointment
		event.db_set("reference_doctype", "Property Appointment")
		event.db_set("reference_docname", appointment.name)
		
	return event
