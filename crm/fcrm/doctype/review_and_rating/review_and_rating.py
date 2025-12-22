from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ReviewAndRating(Document):
	def validate(self):
		"""Validate review data before saving"""
		self._validate_appointment_status()
		self._validate_customer_access()
		self._validate_ratings()
		
		# Auto-populate agent and property from appointment if not set
		if self.appointment and not self.agent:
			appointment_doc = frappe.get_doc("Property Appointment", self.appointment)
			self.agent = appointment_doc.agent
			self.property = appointment_doc.property
			self.customer = appointment_doc.customer

	def before_insert(self):
		"""Set default values"""
		if not self.status:
			self.status = "Draft"

	def before_save(self):
		"""Update submitted_at when status changes to Submitted"""
		if self.status == "Submitted" and not self.submitted_at:
			self.submitted_at = now_datetime()

	def _validate_appointment_status(self):
		"""Ensure appointment is completed before allowing review"""
		if self.appointment:
			appointment_status = frappe.db.get_value("Property Appointment", self.appointment, "status")
			if appointment_status != "Completed":
				frappe.throw(
					_("Reviews can only be submitted for completed appointments."),
					frappe.ValidationError
				)

	def _validate_customer_access(self):
		"""Ensure only the customer who booked can review"""
		if self.appointment and self.customer:
			appointment_customer = frappe.db.get_value("Property Appointment", self.appointment, "customer")
			if appointment_customer != self.customer:
				frappe.throw(
					_("You can only review appointments that you booked."),
					frappe.PermissionError
				)

	def _validate_ratings(self):
		"""Validate rating values are within valid range"""
		for rating_field in ["overall_rating", "agent_rating", "property_rating"]:
			rating = getattr(self, rating_field, 0) or 0
			if rating < 0:
				frappe.throw(
					_("{0} cannot be negative.").format(rating_field.replace("_", " ").title()),
					frappe.ValidationError
				)
			if rating > 5:
				frappe.throw(
					_("{0} cannot be greater than 5.").format(rating_field.replace("_", " ").title()),
					frappe.ValidationError
				)

