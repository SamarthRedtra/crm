from __future__ import annotations

from frappe.model.document import Document
from frappe.utils import flt


class AgencyBillingInvoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.agency_billing_invoice_item.agency_billing_invoice_item import AgencyBillingInvoiceItem
		from frappe.types import DF

		agency: DF.Link
		billing_period_end: DF.Date
		billing_period_start: DF.Date
		currency: DF.Link
		due_date: DF.Date | None
		error_message: DF.SmallText | None
		invoice_date: DF.Date
		items: DF.Table[AgencyBillingInvoiceItem]
		paid_on: DF.Datetime | None
		status: DF.Literal["Draft", "Open", "Paid", "Failed", "Cancelled"]
		stripe_customer_id: DF.Data | None
		stripe_hosted_invoice_url: DF.Data | None
		stripe_invoice_id: DF.Data | None
		stripe_payment_intent_id: DF.Data | None
		stripe_status: DF.Data | None
		subtotal: DF.Currency
		total: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.subtotal = flt(sum(flt(row.amount or 0) for row in self.items))
		self.total = self.subtotal
