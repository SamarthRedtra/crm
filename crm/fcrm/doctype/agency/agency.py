# Copyright (c) 2026, Redtra Technologies FZE LLC and Contributors
# See license.txt

from frappe.model.document import Document


class Agency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_line1: DF.Data | None
		address_line2: DF.Data | None
		agency_name: DF.Data
		brn_id: DF.Data | None
		city: DF.Data | None
		country: DF.Link | None
		description: DF.TextEditor | None
		email: DF.Data | None
		logo: DF.AttachImage | None
		phone: DF.Data | None
		pincode: DF.Data | None
		state: DF.Data | None
		status: DF.Literal["Active", "Inactive"]
		website: DF.Data | None
	# end: auto-generated types

	pass
