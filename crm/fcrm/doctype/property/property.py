from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class Property(Document):
	STATUS_FLOW = {
		"Draft": {"Draft", "Under Verification"},
		"Under Verification": {"Draft", "Under Verification", "Active", "Inactive"},
		"Active": {"Active", "Inactive"},
		"Inactive": {"Inactive", "Draft"},
	}

	def before_insert(self):
		self._set_property_code()

	def before_validate(self):
		self._set_property_code()

	def validate(self):
		self._validate_price()
		self._validate_coordinates()
		self._validate_status_transition()
		self._ensure_verified_agent()

	def _set_property_code(self):
		if not self.property_code:
			# Use naming series fallback to document name if already generated
			self.property_code = self.name or ""

	def _validate_price(self):
		if self.price is not None and self.price < 0:
			frappe.throw(_("Price must be greater than or equal to zero."))

	def _validate_coordinates(self):
		if self.latitude is not None and (self.latitude < -90 or self.latitude > 90):
			frappe.throw(_("Latitude must be between -90 and 90 degrees."))
		if self.longitude is not None and (self.longitude < -180 or self.longitude > 180):
			frappe.throw(_("Longitude must be between -180 and 180 degrees."))

	def _validate_status_transition(self):
		if self.is_new():
			return
		previous_status = self.get_db_value("status")
		if not previous_status:
			return
		allowed = self.STATUS_FLOW.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Invalid status change from {0} to {1}.").format(previous_status, self.status)
			)

	def _ensure_verified_agent(self):
		if not self.agent:
			return

		agent_status = frappe.db.get_value("Agent", self.agent, "status")
		if not agent_status:
			frappe.throw(_("Agent {0} does not exist.").format(self.agent))
		if agent_status != "Verified":
			frappe.throw(
				_("Agent {0} must be verified before the property can be saved.").format(self.agent)
			)

