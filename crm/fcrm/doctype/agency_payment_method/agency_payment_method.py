from __future__ import annotations

from frappe.model.document import Document


class AgencyPaymentMethod(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		added_on: DF.Datetime | None
		agency: DF.Link
		brand: DF.Data | None
		detached_on: DF.Datetime | None
		exp_month: DF.Int
		exp_year: DF.Int
		is_default: DF.Check
		last4: DF.Data | None
		status: DF.Literal["Active", "Detached"]
		stripe_customer_id: DF.Data
		stripe_payment_method_id: DF.Data
		type: DF.Data | None
	# end: auto-generated types

	pass
