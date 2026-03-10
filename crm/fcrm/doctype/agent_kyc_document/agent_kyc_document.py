from __future__ import annotations

from frappe.model.document import Document


class AgentKYCDocument(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		admin_comment: DF.SmallText | None
		doc_status: DF.Literal["Pending", "Approved", "Rejected"]
		document_file: DF.Attach
		document_type: DF.Literal["ID Proof", "Address Proof", "License", "BRN Certificate", "Agency Agreement", "Photo", "Other"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		remarks: DF.SmallText | None
		verified: DF.Check
	# end: auto-generated types

	pass
