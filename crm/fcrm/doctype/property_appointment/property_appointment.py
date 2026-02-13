from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, format_datetime
from crm.api.redtra.utils import get_mandate_agent_verification



class PropertyAppointment(Document):
	OPEN_STATUSES = {"Scheduled"}

	def before_insert(self):
		self._assign_default_agent()

	def validate(self):
		self._assign_default_agent()
		self._validate_timeslot()
		self._validate_agent_status()
		self._prevent_overlap()
		self._enforce_daily_limit()

	def after_insert(self):
		"""Send notifications when appointment is created"""
		"""Send notifications when appointment is created"""
		self.flags.just_created = True
		self._send_appointment_notifications(is_new=True)

	def on_update(self):
		"""Send notifications when appointment is rescheduled (datetime changed) or status changed"""
		# Check if datetime was changed (reschedule)
		datetime_changed = (
			self.has_value_changed("start_datetime") or 
			self.has_value_changed("end_datetime")
		)
		
		# Check if status changed
		status_changed = self.has_value_changed("status")
		
		# Handle reschedule (datetime changed while status remains Scheduled)
		# Handle reschedule (datetime changed while status remains Scheduled)
		# Skip if just created (after_insert already handled notification)
		if datetime_changed and self.status == "Scheduled" and not self.flags.just_created:
			# Appointment was rescheduled - reset reminder status so new reminder can be sent
			if hasattr(self, "reminder_sent") and self.reminder_sent:
				self.reminder_sent = 0
			# Appointment was rescheduled
			self._send_appointment_notifications(is_new=False, is_reschedule=True)
		
		# Handle status changes (cancellation, completion, etc.)
		# Check if status changed to Cancelled or Completed
		if status_changed and self.status in ["Cancelled", "Completed"]:
			self._send_status_change_notification()

	def _assign_default_agent(self):
		if self.agent or not self.property:
			return

		self.agent = frappe.db.get_value("Property", self.property, "agent")

	def _validate_timeslot(self):
		if not self.start_datetime or not self.end_datetime:
			return

		if self.end_datetime <= self.start_datetime:
			frappe.throw(_("End datetime must be later than start datetime."))

	def _validate_agent_status(self):
		if not self.agent:
			frappe.throw(_("Agent is required for the appointment."))

		agent_status = frappe.db.get_value("Agent", self.agent, "status")
		if get_mandate_agent_verification() and agent_status != "Verified":
			frappe.throw(_("Agent {0} must be verified to receive appointments.").format(self.agent))

	def _prevent_overlap(self):
		if not self.agent or self.status not in self.OPEN_STATUSES:
			return

		existing = frappe.db.sql(
			"""
			select name
			from `tabProperty Appointment`
			where agent = %s
			  and status = 'Scheduled'
			  and name != %s
			  and start_datetime < %s
			  and end_datetime > %s
			""",
			(self.agent, self.name or "", self.end_datetime, self.start_datetime),
		)
		if existing:
			frappe.throw(
				_("Agent {0} already has an appointment during the selected slot.").format(self.agent)
			)

	def _enforce_daily_limit(self):
		max_daily = frappe.db.get_value("Agent", self.agent, "max_daily_appointments") or 0
		if not max_daily:
			return

		appointment_date = getdate(self.start_datetime)
		day_start = datetime.combine(appointment_date, datetime.min.time())
		day_end = datetime.combine(appointment_date, datetime.max.time())
		scheduled = frappe.db.count(
			"Property Appointment",
			{
				"agent": self.agent,
				"status": "Scheduled",
				"start_datetime": ["between", [day_start, day_end]],
				"name": ["!=", self.name or ""],
			},
		)

		if scheduled >= max_daily:
			frappe.throw(
				_("Agent {0} has reached the daily appointment limit for {1}.").format(
					self.agent, appointment_date.strftime("%Y-%m-%d")
				)
			)

	def _send_appointment_notifications(self, is_new: bool = True, is_reschedule: bool = False):
		"""Create notifications for both customer and agent when appointment is created or rescheduled"""
		try:
			# Fetch related documents
			if not self.property or not self.agent or not self.customer:
				return

			property_doc = frappe.get_doc("Property", self.property)
			agent_doc = frappe.get_doc("Agent", self.agent)
			customer_doc = frappe.get_doc("Customer", self.customer)

			customer_user = getattr(customer_doc, "user", None)
			agent_user = frappe.db.get_value("Agent", self.agent, "user")

			if not customer_user or not agent_user:
				return

			property_title = property_doc.title or property_doc.name
			appointment_time = format_datetime(self.start_datetime, "dd MMM yyyy, hh:mm a")

			if is_new:
				# New appointment notifications
				# Notification for customer (confirmation)
				customer_notification_text = _("Appointment confirmed for {0}").format(property_title)
				customer_message = _(
					"Your appointment for <b>{0}</b> has been confirmed for <b>{1}</b>. "
					"Agent: {2}"
				).format(
					property_title,
					appointment_time,
					agent_doc.full_name or agent_user,
				)

				self._create_notification(
					from_user=agent_user,
					to_user=customer_user,
					notification_type="Assignment",
					notification_text=customer_notification_text,
					message=customer_message,
				)

				# Notification for agent
				agent_notification_text = _("New appointment booked: {0}").format(property_title)
				agent_message = _(
					"New appointment booked for <b>{0}</b> on <b>{1}</b>. "
					"Customer: {2}"
				).format(
					property_title,
					appointment_time,
					customer_doc.full_name,
				)

				self._create_notification(
					from_user=customer_user,
					to_user=agent_user,
					notification_type="Assignment",
					notification_text=agent_notification_text,
					message=agent_message,
				)

			elif is_reschedule:
				# Reschedule notifications
				# Notification for customer
				customer_notification_text = _("Appointment rescheduled: {0}").format(property_title)
				customer_message = _(
					"Your appointment for <b>{0}</b> has been rescheduled to <b>{1}</b>. "
					"Agent: {2}"
				).format(
					property_title,
					appointment_time,
					agent_doc.full_name or agent_user,
				)

				self._create_notification(
					from_user=agent_user,
					to_user=customer_user,
					notification_type="Assignment",
					notification_text=customer_notification_text,
					message=customer_message,
				)

				# Notification for agent
				agent_notification_text = _("Appointment rescheduled: {0}").format(property_title)
				agent_message = _(
					"Appointment for <b>{0}</b> has been rescheduled to <b>{1}</b>. "
					"Customer: {2}"
				).format(
					property_title,
					appointment_time,
					customer_doc.full_name,
				)

				self._create_notification(
					from_user=customer_user,
					to_user=agent_user,
					notification_type="Assignment",
					notification_text=agent_notification_text,
					message=agent_message,
				)

		except Exception as e:
			# Log error but don't fail the appointment save
			frappe.log_error(
				f"Failed to create appointment notification: {str(e)}",
				"Appointment Notification Error"
			)

	def _send_status_change_notification(self):
		"""Send notification when appointment status changes (Cancelled, Completed, etc.)"""
		try:
			if not self.property or not self.agent or not self.customer:
				return

			property_doc = frappe.get_doc("Property", self.property)
			agent_doc = frappe.get_doc("Agent", self.agent)
			customer_doc = frappe.get_doc("Customer", self.customer)

			customer_user = getattr(customer_doc, "user", None)
			agent_user = frappe.db.get_value("Agent", self.agent, "user")

			if not customer_user or not agent_user:
				return

			property_title = property_doc.title or property_doc.name

			if self.status == "Cancelled":
				# Notify both parties about cancellation
				customer_notification_text = _("Appointment cancelled: {0}").format(property_title)
				customer_message = _("Your appointment for <b>{0}</b> has been cancelled.").format(
					property_title
				)

				self._create_notification(
					from_user=agent_user,
					to_user=customer_user,
					notification_type="Assignment",
					notification_text=customer_notification_text,
					message=customer_message,
				)

				agent_notification_text = _("Appointment cancelled: {0}").format(property_title)
				agent_message = _(
					"Appointment for <b>{0}</b> with customer <b>{1}</b> has been cancelled."
				).format(property_title, customer_doc.full_name)

				self._create_notification(
					from_user=customer_user,
					to_user=agent_user,
					notification_type="Assignment",
					notification_text=agent_notification_text,
					message=agent_message,
				)

			elif self.status == "Completed":
				# Optional: Notify on completion
				customer_notification_text = _("Appointment completed: {0}").format(property_title)
				customer_message = _("Your appointment for <b>{0}</b> has been marked as completed.").format(
					property_title
				)

				self._create_notification(
					from_user=agent_user,
					to_user=customer_user,
					notification_type="Assignment",
					notification_text=customer_notification_text,
					message=customer_message,
				)

		except Exception as e:
			frappe.log_error(
				f"Failed to create status change notification: {str(e)}",
				"Appointment Notification Error"
			)

	def _create_notification(
		self,
		from_user: str,
		to_user: str,
		notification_type: str,
		notification_text: str,
		message: str,
	):
		"""Helper function to create a CRM Notification"""
		try:
			# Validate user fields before creating notification
			if not from_user or not to_user:
				frappe.log_error(
					f"Missing user fields - from_user: {from_user}, to_user: {to_user}",
					"Appointment Notification Error"
				)
				return
			
			# Verify users exist
			if not frappe.db.exists("User", from_user):
				frappe.log_error(
					f"From user does not exist: {from_user}",
					"Appointment Notification Error"
				)
				return
			
			if not frappe.db.exists("User", to_user):
				frappe.log_error(
					f"To user does not exist: {to_user}",
					"Appointment Notification Error"
				)
				return
			
			notification_doc = frappe.get_doc(
				{
					"doctype": "CRM Notification",
					"from_user": from_user,
					"to_user": to_user,
					"type": notification_type,
					"notification_text": notification_text,
					"message": message,
					"notification_type_doctype": "Property Appointment",
					"notification_type_doc": self.name,
					"reference_doctype": "Property Appointment",
					"reference_name": self.name,
					"read": 0,
				}
			)
			notification_doc.flags.ignore_permissions = True
			notification_doc.insert(ignore_permissions=True)
			# Explicitly commit to ensure notification is saved
			frappe.db.commit()
			
			frappe.log_error(
				f"Successfully created notification: {notification_doc.name} for user {to_user}",
				"Appointment Notification Success",
				is_error=False
			)
		except Exception as e:
			frappe.log_error(
				f"Failed to insert notification: {str(e)}\nTraceback: {frappe.get_traceback()}",
				"Appointment Notification Error"
			)