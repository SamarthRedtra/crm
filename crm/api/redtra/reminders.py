from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, format_datetime

from . import utils


@frappe.whitelist()
@utils.require_jwt()
def send_appointment_reminder(appointment_id: str) -> dict[str, Any]:
	"""
	Manually trigger reminder notification for an appointment.
	Can be used by agents or customers to send reminder.
	"""
	appointment_doc = frappe.get_doc("Property Appointment", appointment_id)
	
	# Verify access
	user = utils.get_current_user()
	roles = set(frappe.get_roles(user))
	
	has_access = False
	if "System Manager" in roles:
		has_access = True
	elif "Agent" in roles:
		agent_name = frappe.db.get_value("Agent", {"user": user}, "name")
		if agent_name and appointment_doc.agent == agent_name:
			has_access = True
	else:
		customer = utils.get_customer_by_user(user)
		if customer and appointment_doc.customer == customer.name:
			has_access = True
	
	if not has_access:
		frappe.throw(_("You do not have access to this appointment."), frappe.PermissionError)
	
	# Only send reminders for scheduled appointments
	if appointment_doc.status != "Scheduled":
		frappe.throw(_("Reminders can only be sent for scheduled appointments."), frappe.ValidationError)
	
	# Send reminder notifications
	_send_reminder_notifications(appointment_doc)
	
	return {
		"message": _("Reminder sent successfully."),
		"appointment_id": appointment_id,
	}


def _send_reminder_notifications(appointment_doc):
	"""Send reminder notifications to both customer and agent"""
	try:
		if not appointment_doc.property or not appointment_doc.agent or not appointment_doc.customer:
			return

		property_doc = frappe.get_doc("Property", appointment_doc.property)
		agent_doc = frappe.get_doc("Agent", appointment_doc.agent)
		customer_doc = frappe.get_doc("Customer", appointment_doc.customer)

		customer_user = getattr(customer_doc, "user", None)
		agent_user = frappe.db.get_value("Agent", appointment_doc.agent, "user")

		property_title = property_doc.title or property_doc.name
		appointment_time = format_datetime(appointment_doc.start_datetime, "dd MMM yyyy, hh:mm a")
		sent_any = False
		
		# Reminder for customer
		customer_notification_text = _("Reminder: Appointment in 1 hour - {0}").format(property_title)
		customer_message = _(
			"Reminder: Your appointment for <b>{0}</b> is scheduled in 1 hour at <b>{1}</b>. "
			"Agent: {2}"
		).format(
			property_title,
			appointment_time,
			agent_doc.full_name or agent_user or _("Assigned Agent"),
		)

		if customer_user:
			_create_reminder_notification(
				from_user=agent_user or "Administrator",
				to_user=customer_user,
				notification_text=customer_notification_text,
				message=customer_message,
				appointment_doc=appointment_doc,
			)
			sent_any = True
		elif customer_doc.email:
			_send_email_reminder(
				to_email=customer_doc.email,
				subject=customer_notification_text,
				message=customer_message,
			)
			sent_any = True

		# Reminder for agent
		agent_notification_text = _("Reminder: Appointment in 1 hour - {0}").format(property_title)
		agent_message = _(
			"Reminder: You have an appointment for <b>{0}</b> in 1 hour at <b>{1}</b>. "
			"Customer: {2}"
		).format(
			property_title,
			appointment_time,
			customer_doc.full_name,
		)

		if agent_user:
			_create_reminder_notification(
				from_user=customer_user or "Administrator",
				to_user=agent_user,
				notification_text=agent_notification_text,
				message=agent_message,
				appointment_doc=appointment_doc,
			)
			sent_any = True
		
		# Mark reminder as sent
		if sent_any:
			appointment_doc.db_set("reminder_sent", 1, update_modified=False)
			frappe.db.commit()

	except Exception as e:
		frappe.log_error(
			f"Failed to send appointment reminder: {str(e)}",
			"Appointment Reminder Error"
		)


def _create_reminder_notification(
	from_user: str,
	to_user: str,
	notification_text: str,
	message: str,
	appointment_doc,
):
	"""Helper function to create a reminder notification"""
	try:
		if not from_user or not to_user:
			return
		
		if not frappe.db.exists("User", from_user) or not frappe.db.exists("User", to_user):
			return
		
		notification_doc = frappe.get_doc(
			{
				"doctype": "CRM Notification",
				"from_user": from_user,
				"to_user": to_user,
				"type": "Assignment",
				"notification_text": notification_text,
				"message": message,
				"notification_type_doctype": "Property Appointment",
				"notification_type_doc": appointment_doc.name,
				"reference_doctype": "Property Appointment",
				"reference_name": appointment_doc.name,
				"read": 0,
			}
		)
		notification_doc.flags.ignore_permissions = True
		notification_doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			f"Failed to create reminder notification: {str(e)}",
			"Appointment Reminder Error"
		)


def _send_email_reminder(to_email: str, subject: str, message: str):
	try:
		frappe.sendmail(
			recipients=[to_email],
			subject=subject,
			message=message,
		)
	except Exception as e:
		frappe.log_error(
			f"Failed to send reminder email to {to_email}: {str(e)}",
			"Appointment Reminder Error"
		)


def send_scheduled_reminders():
	"""
	Scheduled job function to automatically send reminders 1 hour before appointments.
	This should be called periodically (every 5-10 minutes) via scheduler.
	"""
	try:
		now = now_datetime()
		# Calculate time window: 55-65 minutes from now (10-minute window to account for scheduler timing)
		reminder_start = now + timedelta(minutes=55)
		reminder_end = now + timedelta(minutes=65)
		
		# Find appointments that need reminders
		# Use raw SQL for better control over datetime filtering
		appointments_to_remind = frappe.db.sql(
			"""
			SELECT name
			FROM `tabProperty Appointment`
			WHERE status = 'Scheduled'
			  AND reminder_sent = 0
			  AND start_datetime >= %(reminder_start)s
			  AND start_datetime <= %(reminder_end)s
			""",
			{
				"reminder_start": reminder_start,
				"reminder_end": reminder_end,
			},
			as_dict=True,
		)
		
		for apt in appointments_to_remind:
			try:
				appointment_doc = frappe.get_doc("Property Appointment", apt.get("name"))
				_send_reminder_notifications(appointment_doc)
				frappe.db.commit()
			except Exception as e:
				frappe.log_error(
					f"Failed to send reminder for appointment {apt.get('name')}: {str(e)}",
					"Appointment Reminder Error"
				)
				frappe.db.rollback()
		
		return {
			"reminders_sent": len(appointments_to_remind),
			"message": _("Reminder check completed."),
		}
	except Exception as e:
		frappe.log_error(
			f"Error in scheduled reminder job: {str(e)}",
			"Appointment Reminder Scheduler Error"
		)

