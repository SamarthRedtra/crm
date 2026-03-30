from __future__ import annotations

from frappe.model.document import Document


class StripeWebhookEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agency: DF.Link | None
		attempt_count: DF.Int
		crm_invoice: DF.Link | None
		event_id: DF.Data
		event_type: DF.Data | None
		last_error: DF.SmallText | None
		metadata_json: DF.SmallText | None
		payload_json: DF.LongText
		payment_intent_id: DF.Data | None
		processed_on: DF.Datetime | None
		received_on: DF.Datetime
		signature_header: DF.SmallText | None
		status: DF.Literal["Received", "Processing", "Processed", "Failed", "Ignored"]
		stripe_status: DF.Data | None
	# end: auto-generated types

	pass
