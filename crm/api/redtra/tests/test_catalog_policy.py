import frappe
from frappe.tests import IntegrationTestCase

from crm.api.redtra import billing


class TestCatalogPolicy(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)

	def test_only_one_agent_level_can_exist(self):
		created = None
		existing = frappe.get_all("Agent Level", pluck="name")
		if not existing:
			created = frappe.get_doc(
				{
					"doctype": "Agent Level",
					"level_name": f"Base {self.suffix}",
					"daily_rate": 100,
					"currency": "AED",
					"active": 1,
				}
			).insert(ignore_permissions=True)

		try:
			with self.assertRaises(frappe.ValidationError):
				frappe.get_doc(
					{
						"doctype": "Agent Level",
						"level_name": f"Extra {self.suffix}",
						"daily_rate": 200,
						"currency": "AED",
						"active": 1,
					}
				).insert(ignore_permissions=True)
		finally:
			if created:
				frappe.delete_doc("Agent Level", created.name, ignore_permissions=True, force=True)
				frappe.db.commit()

	def test_public_billing_preview_exposes_agent_level_and_addons(self):
		existing_levels = frappe.get_all("Agent Level", pluck="name")
		own_level = None
		if not existing_levels:
			own_level = frappe.get_doc(
				{
					"doctype": "Agent Level",
					"level_name": f"Catalog Base {self.suffix}",
					"daily_rate": 120,
					"currency": "AED",
					"active": 1,
				}
			).insert(ignore_permissions=True)

		canonical = frappe.get_all("Agent Level", pluck="name", order_by="sort_order asc, level_name asc", limit=1)
		expected_level = canonical[0] if canonical else None
		addon_names = []
		try:
			for i in range(2):
				ad = frappe.get_doc(
					{
						"doctype": "Billing Addon",
						"addon_name": f"Addon {self.suffix} {i}",
						"pricing_model": "Daily Fixed",
						"rate": 10 + i,
						"currency": "AED",
						"active": 1,
					}
				).insert(ignore_permissions=True)
				addon_names.append(ad.name)

			frappe.db.commit()

			preview = billing.public_billing_preview()
			self.assertIn("agent_level", preview)
			if expected_level:
				self.assertEqual(preview["agent_level"]["name"], expected_level)
			self.assertLessEqual(len(preview.get("agent_levels") or []), 1)

			catalog_names = {row.get("name") for row in (preview.get("billing_addons") or [])}
			for an in addon_names:
				self.assertIn(an, catalog_names)
		finally:
			for an in addon_names:
				if frappe.db.exists("Billing Addon", an):
					frappe.delete_doc("Billing Addon", an, ignore_permissions=True, force=True)
			if own_level and frappe.db.exists("Agent Level", own_level.name):
				frappe.delete_doc("Agent Level", own_level.name, ignore_permissions=True, force=True)
			frappe.db.commit()
