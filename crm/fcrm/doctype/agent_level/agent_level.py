from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class AgentLevel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		currency: DF.Link
		daily_rate: DF.Currency
		description: DF.SmallText | None
		level_name: DF.Data
		sort_order: DF.Int
	# end: auto-generated types

	def validate(self):
		self.level_name = (self.level_name or "").strip()
		if not self.level_name:
			frappe.throw(_("Level name is required."))
