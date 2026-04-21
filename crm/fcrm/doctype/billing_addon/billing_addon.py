from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class BillingAddon(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		addon_name: DF.Data
		currency: DF.Link
		description: DF.SmallText | None
		pricing_model: DF.Literal["Daily Fixed", "Monthly Fixed", "Usage Based"]
		rate: DF.Currency
		sort_order: DF.Int
		unit_label: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.addon_name = (self.addon_name or "").strip()
		if not self.addon_name:
			frappe.throw(_("Addon name is required."))
