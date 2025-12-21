# Copyright (c) 2025, Redtra Technologies FZE LLC and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PropertySetting(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		mandate_agent_verification: DF.Check
	# end: auto-generated types

	pass
