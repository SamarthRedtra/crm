# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import get_controller
from frappe.tests import UnitTestCase
from unittest.mock import patch

from crm.api.doc import get_data
from crm.fcrm.doctype.crm_view_settings.crm_view_settings import create_or_update_standard_view


class TestProperty(UnitTestCase):
	def test_status_options_include_dld_statuses(self):
		controller = get_controller("Property")
		self.assertIn("Pending DLD", controller.STATUS_FLOW)
		self.assertIn("Rejected DLD", controller.STATUS_FLOW)
		self.assertIn("Pending DLD", controller.STATUS_FLOW["Under Verification"])
		self.assertIn("Rejected DLD", controller.STATUS_FLOW["Under Verification"])

	def test_default_list_data_is_available_on_controller(self):
		controller = get_controller("Property")

		self.assertTrue(hasattr(controller, "default_list_data"))

		list_data = controller.default_list_data()
		self.assertEqual(
			["name", "title", "status", "listing_type", "price", "currency", "agent", "property_type", "city", "modified"],
			list_data["rows"],
		)
		self.assertEqual("title", list_data["columns"][0]["key"])

	def test_default_kanban_settings_is_available_on_controller(self):
		controller = get_controller("Property")

		self.assertTrue(hasattr(controller, "default_kanban_settings"))

		settings = controller.default_kanban_settings()
		self.assertEqual("status", settings["column_field"])
		self.assertEqual("title", settings["title_field"])

	def test_get_data_falls_back_to_property_defaults_when_standard_view_is_empty(self):
		create_or_update_standard_view(
			{
				"doctype": "Property",
				"type": "list",
				"columns": "[]",
				"rows": "[]",
				"load_default_columns": 1,
			}
		)

		data = get_data("Property", {}, "modified desc")

		self.assertTrue(data["columns"])
		self.assertEqual("title", data["columns"][0]["key"])
		self.assertIn("title", data["rows"])

	def test_before_validate_clears_rent_type_for_buy_listing(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"listing_type": "Buy",
				"rent_type": "Monthly",
			}
		)

		doc.run_method("before_validate")

		self.assertEqual("", doc.rent_type)

	def test_validate_rejects_negative_price(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"price": -10,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			doc.run_method("validate")

	def test_validate_rejects_invalid_coordinates(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"latitude": 91,
				"longitude": 181,
			}
		)

		with self.assertRaises(frappe.ValidationError):
			doc.run_method("validate")

	def test_validate_rejects_property_type_outside_category(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"property_category": "Residential",
				"property_type": "Office",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			doc.run_method("validate")

	def test_validate_allows_commercial_shop(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"title": "Test Shop",
				"property_category": "Commercial",
				"property_type": "Shop",
				"agent": "Test Agent", # Placeholder
				"price": 1000,
				"currency": "AED",
				"listing_type": "Buy"
			}
		)
		# We don't call doc.insert() because it requires db setup, 
		# but validate() should pass now that 'Shop' is in property.json options
		# and COMMERCIAL_TYPES.
		doc.run_method("validate")

	def test_reverification_triggers_for_non_featured_updates(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"status": "Active",
				"title": "Updated Title",
			}
		)
		doc.is_new = lambda: False
		doc.get_doc_before_save = lambda: frappe._dict(status="Active")
		doc.has_value_changed = lambda fieldname: fieldname == "title"

		doc.run_method("before_validate")

		self.assertEqual("Under Verification", doc.status)

	def test_reverification_triggers_on_trakheesi_identity_change(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"status": "Active",
				"trakheesi_permit_number": "P-NEW",
			}
		)
		doc.is_new = lambda: False
		doc.get_doc_before_save = lambda: frappe._dict(status="Active")
		doc.has_value_changed = lambda fieldname: fieldname == "trakheesi_permit_number"

		doc.run_method("before_validate")

		self.assertEqual("Under Verification", doc.status)

	def test_reverification_ignores_trakheesi_api_sync_fields(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"status": "Active",
				"trakheesi_listing_guid": "guid-123",
			}
		)
		doc.is_new = lambda: False
		doc.get_doc_before_save = lambda: frappe._dict(status="Active")
		doc.has_value_changed = lambda fieldname: fieldname == "trakheesi_listing_guid"

		doc.run_method("before_validate")

		self.assertEqual("Active", doc.status)

	def test_reverification_ignores_featured_only_changes(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"status": "Active",
				"is_featured": 1,
			}
		)
		doc.is_new = lambda: False
		doc.get_doc_before_save = lambda: frappe._dict(status="Active")
		doc.has_value_changed = lambda fieldname: fieldname == "is_featured"

		doc.run_method("before_validate")

		self.assertEqual("Active", doc.status)

	def test_on_update_logs_featured_changes_from_desk(self):
		doc = frappe.get_doc(
			{
				"doctype": "Property",
				"name": "PROP-UNIT-TEST",
				"agent": "AGENT-UNIT-TEST",
				"is_featured": 1,
				"featured_from": "2026-05-10 00:00:00",
				"featured_until": "2026-05-20 23:59:59",
			}
		)
		doc.get_doc_before_save = lambda: frappe._dict(
			is_featured=0,
			featured_from=None,
			featured_until=None,
		)

		with patch(
			"crm.fcrm.doctype.property.property.featured_logs.create_property_featured_log"
		) as mocked_log:
			doc.run_method("on_update")

		mocked_log.assert_called_once()
		call_kwargs = mocked_log.call_args.kwargs
		self.assertEqual(call_kwargs.get("event_type"), "Activated")
		self.assertEqual(call_kwargs.get("source"), "Desk")
