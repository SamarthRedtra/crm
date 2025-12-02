from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


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
		if agent_status != "Verified":
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

