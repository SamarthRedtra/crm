from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class Customer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email: DF.Data
		full_name: DF.Data
		phone: DF.Data | None
		preferred_city: DF.Data | None
		user: DF.Link
		whatsapp_number: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		self._sync_user_defaults()

	def validate(self):
		self._sync_user_defaults()

	def _sync_user_defaults(self):
		if not self.user:
			return
		try:
			user_doc = frappe.get_cached_doc("User", self.user)
		except frappe.DoesNotExistError as exc:
			frappe.throw(_("Linked user {0} does not exist.").format(self.user), exc=exc)

		self.full_name = self.full_name or user_doc.full_name
		self.email = self.email or user_doc.email or user_doc.user_email

