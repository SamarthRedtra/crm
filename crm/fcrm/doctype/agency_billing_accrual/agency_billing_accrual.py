from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_first_day, get_last_day, getdate


class AgencyBillingAccrual(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accrual_key: DF.Data | None
		addon: DF.Link | None
		agency: DF.Link
		agent: DF.Link | None
		agent_level: DF.Link | None
		amount: DF.Currency
		billing_period_end: DF.Date
		billing_period_start: DF.Date
		currency: DF.Link
		description: DF.Data | None
		entry_type: DF.Literal["Agent Level", "Addon"]
		external_reference: DF.Data | None
		invoice: DF.Link | None
		posting_date: DF.Date
		quantity: DF.Float
		rate: DF.Currency
		status: DF.Literal["Open", "Invoiced", "Paid", "Cancelled"]
	# end: auto-generated types

	def validate(self):
		self.posting_date = getdate(self.posting_date)
		self.billing_period_start = getdate(self.billing_period_start or get_first_day(self.posting_date))
		self.billing_period_end = getdate(self.billing_period_end or get_last_day(self.posting_date))
		self.quantity = flt(self.quantity or 0)
		self.rate = flt(self.rate or 0)
		self.amount = flt(self.quantity * self.rate)
		if not self.description:
			self.description = self._build_default_description()
		if not self.accrual_key:
			self.accrual_key = self._build_accrual_key()
		if self.invoice and self.status == "Open":
			self.status = "Invoiced"

	def _build_default_description(self) -> str:
		if self.entry_type == "Agent Level":
			level = self.agent_level or "Level"
			agent = self.agent or "agency agent"
			return f"{level} daily charge for {agent}"
		addon = self.addon or "Addon"
		return f"{addon} charge"

	def _build_accrual_key(self) -> str:
		reference = self.agent_level or self.addon or self.external_reference or "general"
		return "::".join(
			[
				self.entry_type.lower().replace(" ", "_"),
				self.agency or "",
				self.agent or "",
				str(self.posting_date or ""),
				reference,
				str(self.billing_period_start or ""),
			]
		)
