from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, today
from crm.api.redtra.utils import get_mandate_agent_verification


class Property(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.property_agency.property_agency import PropertyAgency
		from crm.fcrm.doctype.property_amenity.property_amenity import PropertyAmenity
		from crm.fcrm.doctype.property_image.property_image import PropertyImage
		from frappe.types import DF

		address_line1: DF.Data | None
		address_line2: DF.Data | None
		agent: DF.Link
		amenities: DF.Table[PropertyAmenity]
		area: DF.Link | None
		area_sqft: DF.Float
		bathrooms: DF.Int
		bedrooms: DF.Int
		city: DF.Data | None
		completion_status: DF.Literal["All", "Ready", "Off-Plan"]
		country: DF.Link | None
		currency: DF.Link
		description: DF.TextEditor | None
		developer: DF.Link | None
		featured_until: DF.Datetime | None
		furnishing_status: DF.Literal["Furnished", "Semi-Furnished", "Unfurnished"]
		gallery: DF.Table[PropertyImage]
		is_featured: DF.Check
		is_rented: DF.Check
		is_sold: DF.Check
		latitude: DF.Float
		listing_type: DF.Literal["Buy", "Rent"]
		longitude: DF.Float
		off_plan_agencies: DF.TableMultiSelect[PropertyAgency]
		pincode: DF.Data | None
		price: DF.Currency
		primary_image: DF.AttachImage | None
		property_category: DF.Literal["Residential", "Commercial", "Mixed Use"]
		property_code: DF.Data | None
		property_type: DF.Literal["Apartment", "Villa", "Office", "Shop", "Plot", "Other"]
		rent_type: DF.Literal["", "Weekly", "Monthly", "Yearly"]
		state: DF.Data | None
		status: DF.Literal["Draft", "Under Verification", "Active", "Inactive"]
		title: DF.Data
		views_count: DF.Int
	# end: auto-generated types

	STATUS_FLOW = {
		"Draft": {"Draft", "Under Verification"},
		"Under Verification": {"Draft", "Under Verification", "Active", "Inactive"},
		"Active": {"Active", "Inactive"},
		"Inactive": {"Inactive", "Draft"},
	}

	def before_insert(self):
		self._set_property_code()

	def before_validate(self):
		self._set_property_code()
		if self.listing_type == "Buy":
			self.rent_type = ""

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
		self._validate_price()
		self._validate_coordinates()
		self._validate_property_type_for_category()
		self._validate_status_transition()
		self._ensure_active_developer()
		self._ensure_verified_agent()
		self._enforce_property_code_rules()

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


@frappe.whitelist()
def create_transaction_from_mark(
	property: str,
	agent: str,
	transaction_type: str,
	amount: float | None = None,
	currency: str | None = None,
	customer: str | None = None,
	rent_type: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Create a Property Transaction Log when marking property as sold/rented from the form."""
	if not frappe.db.exists("Property", property):
		frappe.throw(_("Property not found"), frappe.DoesNotExistError)
	if not frappe.db.exists("Agent", agent):
		frappe.throw(_("Agent not found"), frappe.DoesNotExistError)
	if transaction_type not in ("Sold", "Rented"):
		frappe.throw(_("Transaction type must be Sold or Rented"))

	prop = frappe.get_cached_doc("Property", property)
	currency = currency or prop.currency

	doc = frappe.get_doc(
		{
			"doctype": "Property Transaction Log",
			"property": property,
			"agent": agent,
			"customer": customer,
			"transaction_date": today(),
			"transaction_type": transaction_type,
			"rent_type": rent_type if transaction_type == "Rented" else None,
			"amount": amount,
			"currency": currency,
			"notes": notes,
		}
	)
	doc.insert(ignore_permissions=True)

	if transaction_type == "Sold":
		frappe.db.set_value("Property", property, "is_sold", 1)
	elif transaction_type == "Rented":
		frappe.db.set_value("Property", property, "is_rented", 1)
		if rent_type:
			frappe.db.set_value("Property", property, "rent_type", rent_type)

	return {"name": doc.name}

