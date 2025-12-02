from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class FavoriteProperty(Document):
	def before_insert(self):
		self._ensure_timestamp()

	def validate(self):
		self._prevent_duplicates()

	def _ensure_timestamp(self):
		if not self.created_at:
			self.created_at = now_datetime()

	def _prevent_duplicates(self):
		exists = frappe.db.exists(
			"Favorite Property",
			{
				"user": self.user,
				"property": self.property,
				"name": ["!=", self.name or ""],
			},
		)
		if exists:
			frappe.throw(_("Property is already marked as favorite."))

