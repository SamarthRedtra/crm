from __future__ import annotations

from frappe.model.document import Document


class AgencyBillingInvoiceItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		addon: DF.Link | None
		agent: DF.Link | None
		agent_level: DF.Link | None
		amount: DF.Currency
		description: DF.Data
		entry_type: DF.Literal["Agent Level", "Addon"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quantity: DF.Float
		rate: DF.Currency
		source_accrual: DF.Link | None
	# end: auto-generated types

	pass
