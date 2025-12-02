from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class Agent(Document):
	STATUS_FLOW = {
		"Draft": {"Draft", "Pending Verification"},
		"Pending Verification": {"Draft", "Pending Verification", "Verified", "Rejected"},
		"Verified": {"Pending Verification", "Verified"},
		"Rejected": {"Pending Verification", "Rejected"},
	}

	def validate(self):
		self._sync_user_details()
		self._validate_status_transition()
		self._validate_daily_limit()

	def _sync_user_details(self):
		if not self.user:
			return

		try:
			user_doc = frappe.get_cached_doc("User", self.user)
		except frappe.DoesNotExistError as exc:
			frappe.throw(_("Linked user {0} does not exist.").format(self.user), exc=exc)

		if not user_doc.enabled:
			frappe.throw(_("Linked user {0} is disabled.").format(self.user))

		self.full_name = user_doc.full_name
		self.email = user_doc.email or user_doc.user_email

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

	def _validate_daily_limit(self):
		if self.max_daily_appointments is not None and self.max_daily_appointments < 0:
			frappe.throw(_("Max daily appointments cannot be negative."))

