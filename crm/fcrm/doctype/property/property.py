from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, today
from crm.api.redtra.utils import get_mandate_agent_verification
from crm.api.redtra import featured_logs, trakheesi


class Property(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.off_plan_payment_installment.off_plan_payment_installment import OffPlanPaymentInstallment
		from crm.fcrm.doctype.project_unit.project_unit import ProjectUnit
		from crm.fcrm.doctype.property_agency.property_agency import PropertyAgency
		from crm.fcrm.doctype.property_amenity.property_amenity import PropertyAmenity
		from crm.fcrm.doctype.property_image.property_image import PropertyImage
		from frappe.types import DF

		address_line1: DF.Data | None
		address_line2: DF.Data | None
		agency: DF.Link | None
		agent: DF.Link | None
		amenities: DF.Table[PropertyAmenity]
		area: DF.Link | None
		area_sqft: DF.Float
		bathrooms: DF.Int
		bedrooms: DF.Int
		city: DF.Data | None
		completion_percentage: DF.Literal["", "0-25%", "25-50%", "50-75%", "75-100%"]
		completion_status: DF.Literal["All", "Ready", "Off-Plan"]
		country: DF.Link | None
		currency: DF.Link
		description: DF.TextEditor | None
		developer: DF.Link | None
		featured_from: DF.Datetime | None
		featured_until: DF.Datetime | None
		furnishing_status: DF.Literal["Furnished", "Semi-Furnished", "Unfurnished"]
		gallery: DF.Table[PropertyImage]
		handover_quarter: DF.Literal["", "Q1", "Q2", "Q3", "Q4"]
		handover_year: DF.Literal["", "2024", "2025", "2026", "2027", "2028", "2029", "2030", "2031", "2032", "2033", "2034", "2035"]
		is_featured: DF.Check
		is_rented: DF.Check
		is_sold: DF.Check
		latitude: DF.Float
		license_number: DF.Data | None
		listing_type: DF.Literal["Buy", "Rent"]
		longitude: DF.Float
		off_plan_agencies: DF.TableMultiSelect[PropertyAgency]
		payment_plan_table: DF.Table[OffPlanPaymentInstallment]
		payment_plan_type: DF.Literal["", "60/40", "50/50", "40/60", "30/70", "70/30", "20/80", "80/20", "10/90", "90/10", "Post-handover", "100% Upfront", "Other"]
		pincode: DF.Data | None
		price: DF.Currency
		primary_image: DF.AttachImage | None
		project_units_table: DF.Table[ProjectUnit]
		property_category: DF.Literal["Residential", "Commercial"]
		property_code: DF.Data | None
		property_type: DF.Literal["Apartment", "Villa", "Townhouse", "Penthouse", "Villa Compound", "Hotel Apartment", "Land", "Floor", "Building", "Office", "Shop", "Warehouse", "Labour Camp", "Bulk Unit", "Factory", "Industrial Land", "Mixed Use Land", "Showroom", "Other Commercial", "Plot", "Other"]
		quality_score: DF.Data | None
		rent_type: DF.Literal["", "Daily", "Weekly", "Monthly", "Yearly"]
		state: DF.Data | None
		status: DF.Literal["Draft", "Under Verification", "Pending DLD", "Rejected DLD", "Active", "Inactive"]
		title: DF.Data
		trakheesi_last_verified_on: DF.Datetime | None
		trakheesi_listing_guid: DF.Data | None
		trakheesi_listing_number: DF.Data | None
		trakheesi_permit_number: DF.Data | None
		trakheesi_qr_code: DF.AttachImage | None
		trakheesi_validation_url: DF.Data | None
		trakheesi_verification_payload: DF.LongText | None
		views_count: DF.Int
		zone_name: DF.Data | None
	# end: auto-generated types

	STATUS_FLOW = {
		"Draft": {"Draft", "Under Verification"},
		"Under Verification": {"Draft", "Under Verification", "Pending DLD", "Rejected DLD", "Active", "Inactive"},
		"Pending DLD": {"Pending DLD", "Rejected DLD", "Under Verification", "Active", "Inactive"},
		"Rejected DLD": {"Rejected DLD", "Under Verification", "Pending DLD", "Active", "Inactive"},
		"Active": {"Active", "Inactive", "Under Verification", "Pending DLD", "Rejected DLD"},
		"Inactive": {"Inactive", "Draft", "Under Verification", "Pending DLD", "Rejected DLD"},
	}

	REVERIFICATION_TRIGGER_STATUSES = {"Active", "Inactive"}
	REVERIFICATION_IGNORED_FIELDS = {
		"is_featured",
		"featured_from",
		"featured_until",
		"status",
		"modified",
		"modified_by",
		"creation",
		"owner",
		# Populated by Trakheesi verify API — must not re-trigger verification on sync
		"trakheesi_listing_guid",
		"trakheesi_validation_url",
		"trakheesi_last_verified_on",
		"trakheesi_verification_payload",
	}
	TRAKHEESI_IDENTITY_FIELDS = (
		"trakheesi_listing_number",
		"license_number",
		"trakheesi_permit_number",
		"trakheesi_qr_code",
	)
	NON_VALUE_FIELDTYPES = {
		"Section Break",
		"Column Break",
		"Tab Break",
		"Button",
		"HTML",
		"Image",
		"Fold",
		"Heading",
	}

	def before_insert(self):
		self._set_property_code()
		if self.trakheesi_permit_number and not self.license_number:
			self.license_number = self.trakheesi_permit_number

	def after_insert(self):
		self._log_featured_change(source=(getattr(self.flags, "featured_log_source", None) or "Desk"))

	def before_validate(self):
		self._set_property_code()
		if self.listing_type == "Buy":
			self.rent_type = ""
			self.is_rented = 0
		elif self.listing_type == "Rent":
			self.is_sold = 0
		
		if self.agent and not self.agency:
			self.agency = frappe.db.get_value("Agent", self.agent, "agency")

		self._apply_reverification_on_update()

	def on_update(self):
		self._log_featured_change(source=(getattr(self.flags, "featured_log_source", None) or "Desk"))

	RESIDENTIAL_TYPES = frozenset(
		{
			"Apartment", "Villa", "Townhouse", "Penthouse", "Villa Compound", "Hotel Apartment",
			"Land", "Floor", "Building", "Plot", "Other",  # Plot, Other for backward compatibility
		}
	)
	COMMERCIAL_TYPES = frozenset(
		{
			"Office", "Shop", "Warehouse", "Labour Camp", "Villa", "Bulk Unit", "Land", "Floor",
			"Building", "Factory", "Industrial Land", "Mixed Use Land", "Showroom", "Other Commercial",
			"Plot", "Other",  # Plot, Other for backward compatibility
		}
	)

	def validate(self):
		# self._validate_quality_score()
		self._validate_price()
		self._validate_coordinates()
		self._validate_property_type_for_category()
		self._validate_status_transition()
		self._ensure_active_developer()
		self._ensure_verified_agent()
		self._enforce_property_code_rules()
		self._verify_trakheesi_listing_if_applicable()

	def _should_skip_trakheesi_hooks(self) -> bool:
		if getattr(self.flags, "skip_trakheesi_verification", False):
			return True
		return False

	def _is_import_context(self) -> bool:
		return bool(getattr(frappe.flags, "in_import", False))

	def _has_trakheesi_identity_changes(self) -> bool:
		for fieldname in self.TRAKHEESI_IDENTITY_FIELDS:
			if self.has_value_changed(fieldname):
				return True
		return False

	def _verify_trakheesi_listing_if_applicable(self) -> None:
		if self._should_skip_trakheesi_hooks():
			return

		listing = (self.trakheesi_listing_number or "").strip()
		license_no = (self.license_number or "").strip()

		if not listing and not license_no:
			return

		if not listing or not license_no:
			frappe.throw(
				_("Trakheesi Listing Number and License Number are both required when either is provided."),
				frappe.ValidationError,
			)

		if not (self.trakheesi_permit_number or "").strip():
			frappe.throw(_("Trakheesi Permit Number is mandatory."), frappe.ValidationError)
		if not self._is_import_context() and not (self.trakheesi_qr_code or "").strip():
			frappe.throw(_("Trakheesi QR Code is mandatory."), frappe.ValidationError)

		if not self._has_trakheesi_identity_changes():
			return

		self.status = "Under Verification"
		verification = trakheesi.verify_listing(
			listing_number=listing,
			license_number=license_no,
			reference_doctype="Property",
			reference_docname=self.name if not self.is_new() else None,
		)
		trakheesi.apply_verification_to_property(self, verification)

	def _validate_quality_score(self):
		"""Quality Score is mandatory for Admins/Managers."""
		if frappe.flags.in_import:
			return

		from crm.api.redtra.permissions import _is_internal_manager

		if _is_internal_manager(frappe.session.user):
			if not self.quality_score:
				frappe.throw(_("Quality Score is mandatory for Admin review."), title=_("Missing Scoring"))

	def _validate_property_type_for_category(self):
		if not self.property_type or not self.property_category:
			return
		if self.property_category == "Residential":
			allowed = self.RESIDENTIAL_TYPES
		elif self.property_category == "Commercial":
			allowed = self.COMMERCIAL_TYPES
		else:
			return  # Legacy or unknown category, skip
		if self.property_type not in allowed:
			frappe.throw(
				_("Property type {0} is not valid for category {1}.").format(
					frappe.bold(self.property_type),
					frappe.bold(self.property_category),
				)
			)

	def _set_property_code(self):
		if not self.property_code:
			# Use naming series fallback to document name if already generated
			self.property_code = self.name or ""

	def _validate_price(self):
		if self.price is not None and self.price < 0:
			frappe.throw(_("Price must be greater than or equal to zero."))

	def _validate_coordinates(self):
		if self.latitude is not None and (self.latitude < -90 or self.latitude > 90):
			frappe.throw(_("Latitude must be between -90 and 90 degrees."))
		if self.longitude is not None and (self.longitude < -180 or self.longitude > 180):
			frappe.throw(_("Longitude must be between -180 and 180 degrees."))

	def _validate_status_transition(self):
		if self.is_new():
			return
		previous_status = self.get_db_value("status")
		if not previous_status:
			return
		allowed = self.STATUS_FLOW.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Invalid status change from {0} to {1}.").format(previous_status, self.status)
			)

	def _apply_reverification_on_update(self):
		"""Move edited Active/Inactive properties back to Under Verification."""
		if self.is_new():
			return

		previous = self.get_doc_before_save()
		if not previous:
			return

		if (previous.status or "").strip() not in self.REVERIFICATION_TRIGGER_STATUSES:
			return

		if self._has_non_featured_changes():
			self.status = "Under Verification"

	def _has_non_featured_changes(self) -> bool:
		for field in self.meta.fields:
			fieldname = (field.fieldname or "").strip()
			if not fieldname:
				continue
			if field.fieldtype in self.NON_VALUE_FIELDTYPES:
				continue
			if fieldname in self.REVERIFICATION_IGNORED_FIELDS:
				continue
			if self.has_value_changed(fieldname):
				return True
		return False

	def _log_featured_change(self, source: str):
		previous = self.get_doc_before_save()
		previous_state = (
			{
				"is_featured": cint(previous.get("is_featured")),
				"featured_from": previous.get("featured_from"),
				"featured_until": previous.get("featured_until"),
			}
			if previous
			else None
		)
		current_state = {
			"is_featured": cint(self.is_featured),
			"featured_from": getattr(self, "featured_from", None),
			"featured_until": getattr(self, "featured_until", None),
		}
		event_type = featured_logs.infer_featured_event_type(previous_state, current_state)
		if not event_type:
			return
		featured_logs.create_property_featured_log(
			self.name,
			agent=self.agent,
			event_type=event_type,
			source=source,
			featured_from=current_state["featured_from"],
			featured_until=current_state["featured_until"],
			notes="Featured settings changed from Property form.",
		)

	def _ensure_verified_agent(self):
		if not get_mandate_agent_verification():
			return

		if not self.agent:
			return

		agent_status = frappe.db.get_value("Agent", self.agent, "status")
		if not agent_status:
			frappe.throw(_("Agent {0} does not exist.").format(self.agent))
		if agent_status != "Verified":
			frappe.throw(
				_("Agent {0} must be verified before the property can be saved.").format(self.agent)
			)

	def _ensure_active_developer(self):
		if not self.developer:
			return

		status = frappe.db.get_value("Developer", self.developer, "status")
		if not status:
			frappe.throw(_("Developer {0} does not exist.").format(self.developer))
		if status != "Active":
			frappe.throw(
				_("Developer {0} must be active before the property can be saved.").format(self.developer)
			)

	def _enforce_property_code_rules(self):
		if not self.property_code or not self.agent:
			return

		filters = {
			"property_code": self.property_code,
			"agent": self.agent,
		}
		if not self.is_new():
			filters["name"] = ["!=", self.name]

		if frappe.db.exists("Property", filters):
			frappe.throw(
				_("Agent {0} already has a property with code {1}.").format(
					frappe.bold(self.agent),
					frappe.bold(self.property_code),
				)
			)

		settings = frappe.get_cached_doc("FCRM Settings", "FCRM Settings")
		limit = cint(getattr(settings, "max_agents_per_property_code", 0) or 0)
		if limit <= 0:
			return

		existing_agents = set(
			agent
			for agent in frappe.get_all(
				"Property",
				filters={
					"property_code": self.property_code,
					"name": ["!=", self.name],
				},
				pluck="agent",
				distinct=True,
			)
			if agent
		)

		existing_agents.add(self.agent)

		if len(existing_agents) > limit:
			agents_display = ", ".join(sorted(existing_agents))
			frappe.throw(
				_("Property code {0} cannot be assigned to more than {1} agents. Currently assigned to: {2}.").format(
					frappe.bold(self.property_code),
					limit,
					agents_display,
				)
			)

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Title",
				"type": "Data",
				"key": "title",
				"width": "15rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "10rem",
			},
			{
				"label": "Listing Type",
				"type": "Select",
				"key": "listing_type",
				"width": "8rem",
			},
			{
				"label": "Price",
				"type": "Currency",
				"key": "price",
				"align": "right",
				"width": "9rem",
			},
			{
				"label": "Agent",
				"type": "Link",
				"key": "agent",
				"options": "Agent",
				"width": "11rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"title",
			"status",
			"listing_type",
			"price",
			"currency",
			"agent",
			"property_type",
			"city",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "title",
			"kanban_fields": '["price", "listing_type", "agent", "modified"]',
		}


@frappe.whitelist()
def create_transaction_from_mark(
	property: str,
	agent: str,
	transaction_type: str,
	amount: float | None = None,
	currency: str | None = None,
	customer: str | None = None,
	rent_type: str | None = None,
	start_date: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Create a Property Transaction Log when marking property as sold/rented from the form."""
	if not frappe.db.exists("Property", property):
		frappe.throw(_("Property not found"), frappe.DoesNotExistError)
	if not frappe.db.exists("Agent", agent):
		frappe.throw(_("Agent not found"), frappe.DoesNotExistError)
	if transaction_type not in ("Sold", "Rented", "Sale", "Rent"):
		frappe.throw(_("Transaction type must be Sold or Rented (or Sale/Rent)"))

	# Resolve transaction type based on doctype options
	options = frappe.get_meta("Property Transaction Log").get_field("transaction_type").options or ""
	options_list = [o.strip() for o in options.split("\n") if o.strip()]
	
	resolved_type = transaction_type
	if resolved_type == "Sold" and "Sale" in options_list:
		resolved_type = "Sale"
	elif resolved_type == "Sale" and "Sold" in options_list:
		resolved_type = "Sold"
	elif resolved_type == "Rented" and "Rent" in options_list:
		resolved_type = "Rent"
	elif resolved_type == "Rent" and "Rented" in options_list:
		resolved_type = "Rented"

	prop = frappe.get_cached_doc("Property", property)
	currency = currency or prop.currency

	doc = frappe.get_doc(
		{
			"doctype": "Property Transaction Log",
			"property": property,
			"agent": agent,
			"customer": customer,
			"transaction_date": today(),
			"transaction_type": resolved_type,
			"rent_type": rent_type if transaction_type in ("Rented", "Rent") else None,
			"start_date": start_date if transaction_type in ("Rented", "Rent") else None,
			"amount": amount,
			"currency": currency,
			"notes": notes,
		}
	)
	doc.insert(ignore_permissions=True)

	if transaction_type in ("Sold", "Sale"):
		frappe.db.set_value("Property", property, "is_sold", 1)
	elif transaction_type in ("Rented", "Rent"):
		frappe.db.set_value("Property", property, "is_rented", 1)
		if rent_type:
			frappe.db.set_value("Property", property, "rent_type", rent_type)

	return {
		"name": doc.name,
		"property": property,
		"transaction_type": resolved_type,
	}

