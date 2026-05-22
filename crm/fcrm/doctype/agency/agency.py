# Copyright (c) 2026, Redtra Technologies FZE LLC and Contributors
# See license.txt

from frappe.model.document import Document


class Agency(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.agency_billing_addon.agency_billing_addon import AgencyBillingAddon
		from frappe.types import DF

		address_line1: DF.Data | None
		address_line2: DF.Data | None
		agency_name: DF.Data
		billing_addons: DF.Table[AgencyBillingAddon]
		billing_contact_name: DF.Data | None
		billing_currency: DF.Link | None
		billing_email: DF.Data | None
		billing_start_date: DF.Date | None
		billing_status: DF.Literal["Not Configured", "Active", "Past Due", "Suspended"]
		brn_id: DF.Data
		city: DF.Data | None
		company_license_number: DF.Data | None
		country: DF.Link | None
		description: DF.TextEditor | None
		email: DF.Data
		is_on_trial: DF.Check
		logo: DF.AttachImage | None
		onboarding_status: DF.Literal["Not Started", "In Progress", "Completed"]
		phone: DF.Data
		pincode: DF.Data | None
		rera_id: DF.Data
		state: DF.Data | None
		status: DF.Literal["Active", "Inactive"]
		stripe_customer_id: DF.Data | None
		stripe_default_payment_method_id: DF.Data | None
		trial_end_date: DF.Date | None
		trial_grace_end_date: DF.Date | None
		trial_start_date: DF.Date | None
		trial_status: DF.Literal["Not Started", "Active", "Grace", "Expired", "Converted"]
		verification_notes: DF.SmallText | None
		verification_status: DF.Literal["Pending Verification", "Verified", "Rejected"]
		verified_by: DF.Link | None
		verified_on: DF.Datetime | None
		website: DF.Data | None
		whatsapp_number: DF.Data
	# end: auto-generated types

	pass
