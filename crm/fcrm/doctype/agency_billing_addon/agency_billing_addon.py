from __future__ import annotations

from frappe.model.document import Document


class AgencyBillingAddon(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		addon: DF.Link
		custom_rate: DF.Currency | None
		enabled: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		quantity: DF.Float
	# end: auto-generated types

	pass
