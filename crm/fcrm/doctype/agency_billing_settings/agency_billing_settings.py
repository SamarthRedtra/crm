from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class AgencyBillingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		billing_enabled: DF.Check
		default_currency: DF.Link | None
		invoice_due_days: DF.Int
		payment_mode: DF.Literal["after_verification", "before_verification", "two_step"] | None
		stripe_collection_method: DF.Literal["send_invoice", "charge_automatically"]
		stripe_publishable_key: DF.Data | None
		stripe_secret_key: DF.Password | None
		stripe_webhook_secret: DF.Password | None
		trial_days: DF.Int
		trial_enabled: DF.Check
		trial_grace_days: DF.Int
		trial_requires_payment_method: DF.Check
	# end: auto-generated types

	def validate(self):
		if self.invoice_due_days is not None and self.invoice_due_days < 0:
			frappe.throw(_("Invoice due days cannot be negative."))
		if self.trial_days is not None and self.trial_days < 0:
			frappe.throw(_("Trial days cannot be negative."))
		if self.trial_grace_days is not None and self.trial_grace_days < 0:
			frappe.throw(_("Trial grace days cannot be negative."))
