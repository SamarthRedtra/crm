# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.model.document import get_controller
from frappe.tests import UnitTestCase

from crm.api.doc import get_data
from crm.fcrm.doctype.crm_view_settings.crm_view_settings import create_or_update_standard_view


class TestProperty(UnitTestCase):
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
