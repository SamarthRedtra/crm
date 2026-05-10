
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime
from crm.api.redtra import home, transactions, properties, utils
from unittest.mock import patch

class TestTransactions(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		# Ensure schema is up to date for modified/new doctypes
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_transaction_log", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_featured_log", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_agency", force=True)

		frappe.set_user("Administrator")
		# Create dummy agent user
		self.agent_email = "test_agent_txn@example.com"
		if not frappe.db.exists("User", self.agent_email):
			frappe.get_doc({
				"doctype": "User",
				"email": self.agent_email,
				"first_name": "Test Agent Txn",
				"send_welcome_email": 0,
				"roles": [{"role": "Agent"}, {"role": "System Manager"}] # Start with sys manager to create agent
			}).insert(ignore_permissions=True)
		
		# Create Agent document
		if not frappe.db.exists("Agent", {"user": self.agent_email}):
			self.agent_doc = frappe.get_doc({
				"doctype": "Agent",
				"user": self.agent_email,
				"full_name": "Test Agent Txn",
				"phone": "+971500000010",
				"whatsapp_number": "+971500000010",
				"status": "Verified",
				"dfd_registration_id": "123456789",
				"email": self.agent_email
			}).insert(ignore_permissions=True)
		else:
			self.agent_doc = frappe.get_doc("Agent", {"user": self.agent_email})

		# Create Property
		# Need to be agent to create property via API, or just create directly
		# Let's create directly
		self.property_doc = frappe.get_doc({
			"doctype": "Property",
			"title": "Test Property for Txn",
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"currency": "AED",
			"agent": self.agent_doc.name,
			"status": "Active",
			"is_sold": 0
		}).insert(ignore_permissions=True)

	def tearDown(self):
		self.patcher.stop()
		frappe.set_user("Administrator")
		# Cleanup
		frappe.db.rollback()

	def test_create_transaction_and_is_sold(self):
		# Generate token for agent
		token = utils.generate_jwt(self.agent_email)
		headers = {"Authorization": f"Bearer {token}"}

		# Mock Request
		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "POST"
				self.headers = headers or {}
			
			def get_json(self):
				return self.json

		frappe.local.request = MockRequest({
			"property": self.property_doc.name,
			"transaction_type": "Sold",
			"amount": 1000000,
			"currency": "AED",
			"notes": "Sold!"
		}, headers)

		# Create Transaction
		txn = transactions.create_transaction()
		
		# Verify Transaction created
		self.assertTrue(txn["id"])
		self.assertEqual(txn["property"], self.property_doc.name)
		self.assertEqual(txn["transaction_type"], "Sold")
		self.assertEqual(txn["formatted_amount"], "1M")

		# Verify Property is_sold = 1
		prop = frappe.get_doc("Property", self.property_doc.name)
		self.assertEqual(prop.is_sold, 1)

	def test_create_rent_transaction_and_is_rented(self):
		# Create Property for Rent
		rent_prop = frappe.get_doc({
			"doctype": "Property",
			"title": "Test Property for Rent",
			"listing_type": "Rent",
			"property_type": "Villa",
			"price": 50000,
			"currency": "AED",
			"agent": self.agent_doc.name,
			"status": "Active",
			"is_rented": 0
		}).insert(ignore_permissions=True)

		token = utils.generate_jwt(self.agent_email)
		headers = {"Authorization": f"Bearer {token}"}

		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "POST"
				self.headers = headers or {}
			
			def get_json(self):
				return self.json

		frappe.local.request = MockRequest({
			"property": rent_prop.name,
			"transaction_type": "Rented",
			"rent_type": "Yearly",
			"amount": 50000,
			"currency": "AED",
			"notes": "Rented!"
		}, headers)

		# Create Transaction
		txn = transactions.create_transaction()
		
		# Verify Transaction created
		self.assertTrue(txn["id"])
		self.assertEqual(txn["property"], rent_prop.name)
		self.assertEqual(txn["transaction_type"], "Rented")
		self.assertEqual(txn["rent_type"], "Yearly")
		self.assertEqual(txn["formatted_amount"], "50K")

		# Verify Property is_rented = 1 and rent_type is set
		prop = frappe.get_doc("Property", rent_prop.name)
		self.assertEqual(prop.is_rented, 1)
		self.assertEqual(prop.rent_type, "Yearly")

	def test_list_transactions_guest_and_filters(self):
		# Create an off-plan property
		off_plan_prop = frappe.get_doc({
			"doctype": "Property",
			"title": "Off Plan Villa",
			"listing_type": "Buy",
			"completion_status": "Off-Plan",
			"property_type": "Villa",
			"price": 5000000,
			"currency": "AED",
			"agent": self.agent_doc.name,
			"status": "Active",
			"area_sqft": 5000
		}).insert(ignore_permissions=True)

		# Create transaction for it
		txn_off = frappe.get_doc({
			"doctype": "Property Transaction Log",
			"property": off_plan_prop.name,
			"agent": self.agent_doc.name,
			"transaction_date": "2025-01-01",
			"transaction_type": "Sold",
			"amount": 4500000,
			"currency": "AED"
		}).insert(ignore_permissions=True)

		# 1. Test Guest Access (No Auth Header)
		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "GET"
				self.headers = headers or {}
			def get_json(self): return self.json

		frappe.local.request = MockRequest({}) # No headers
		frappe.form_dict = frappe._dict({"page": 1, "page_size": 10})
		
		res = transactions.list_transactions()
		self.assertGreaterEqual(len(res["items"]), 1)
		
		# 2. Test Off-Plan Filter
		frappe.form_dict = frappe._dict({"off_plan": "1"})
		res_off = transactions.list_transactions()
		
		# Should find the off-plan transaction
		found = any(item["id"] == txn_off.name for item in res_off["items"])
		self.assertTrue(found)
		
		# Verify enriched fields
		for item in res_off["items"]:
			if item["id"] == txn_off.name:
				self.assertEqual(item["formatted_amount"], "4.50M")
				self.assertEqual(item["area_sqft"], 5000)
				self.assertEqual(item["price_per_sqft"], 900.0)
				self.assertEqual(item["formatted_price_per_sqft"], "900.0") # No K/M for 900
				break

	def test_property_api_is_sold(self):
		# Create another property directly and mark as sold
		prop2 = frappe.get_doc({
			"doctype": "Property",
			"title": "Test Property Sold",
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 2000000,
			"currency": "AED",
			"agent": self.agent_doc.name,
			"status": "Active",
			"is_sold": 1
		}).insert(ignore_permissions=True)
		
		token = utils.generate_jwt(self.agent_email)
		headers = {"Authorization": f"Bearer {token}"}
		
		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "GET"
				self.headers = headers or {}
			
			def get_json(self):
				return self.json

		frappe.local.request = MockRequest({}, headers)
		
		# Get Property
		prop_detail = properties.get_property(prop2.name)
		self.assertTrue(prop_detail["is_sold"])
		
		# List Properties
		# We need to ensure we can list it.
		frappe.form_dict = frappe._dict({}) # Reset params
		prop_list = properties.list_properties()
		found = False
		for item in prop_list["items"]:
			if item["id"] == prop2.name:
				self.assertTrue(item["is_sold"])
				found = True
				break
		self.assertTrue(found)

	def test_list_properties_featured_filter_excludes_expired_windows(self):
		active_featured = frappe.get_doc(
			{
				"doctype": "Property",
				"title": "Active Featured Property",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1500000,
				"currency": "AED",
				"agent": self.agent_doc.name,
				"status": "Active",
				"is_featured": 1,
				"featured_from": add_to_date(now_datetime(), days=-1, as_string=True),
				"featured_until": add_to_date(now_datetime(), days=2, as_string=True),
			}
		).insert(ignore_permissions=True)
		expired_featured = frappe.get_doc(
			{
				"doctype": "Property",
				"title": "Expired Featured Property",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1400000,
				"currency": "AED",
				"agent": self.agent_doc.name,
				"status": "Active",
				"is_featured": 1,
				"featured_from": add_to_date(now_datetime(), days=-4, as_string=True),
				"featured_until": add_to_date(now_datetime(), minutes=-10, as_string=True),
			}
		).insert(ignore_permissions=True)

		frappe.form_dict = frappe._dict({"is_featured": "1", "page": 1, "page_size": 50})
		rows = properties.list_properties()["items"]
		property_ids = {item["id"] for item in rows}

		self.assertIn(active_featured.name, property_ids)
		self.assertNotIn(expired_featured.name, property_ids)

	def test_home_featured_properties_exclude_expired_windows(self):
		active_featured = frappe.get_doc(
			{
				"doctype": "Property",
				"title": "Home Active Featured",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1200000,
				"currency": "AED",
				"agent": self.agent_doc.name,
				"status": "Active",
				"is_featured": 1,
				"featured_from": add_to_date(now_datetime(), days=-1, as_string=True),
				"featured_until": add_to_date(now_datetime(), days=1, as_string=True),
			}
		).insert(ignore_permissions=True)
		expired_featured = frappe.get_doc(
			{
				"doctype": "Property",
				"title": "Home Expired Featured",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1150000,
				"currency": "AED",
				"agent": self.agent_doc.name,
				"status": "Active",
				"is_featured": 1,
				"featured_from": add_to_date(now_datetime(), days=-3, as_string=True),
				"featured_until": add_to_date(now_datetime(), minutes=-15, as_string=True),
			}
		).insert(ignore_permissions=True)

		rows = home._get_featured_properties()
		property_ids = {item["id"] for item in rows}

		self.assertIn(active_featured.name, property_ids)
		self.assertNotIn(expired_featured.name, property_ids)

	def test_update_property_api_creates_featured_log(self):
		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "POST"
				self.headers = headers or {}

			def get_json(self):
				return self.json

		frappe.local.request = MockRequest(
			{
				"is_featured": 1,
				"featured_until": add_to_date(now_datetime(), days=3, as_string=True),
			},
			{},
		)
		with patch("crm.api.redtra.utils.extract_bearer_token", return_value="fake"), patch(
			"crm.api.redtra.utils.decode_jwt",
			return_value={"user": self.agent_email},
		):
			properties.update_property(self.property_doc.name)

		logs = frappe.get_all(
			"Property Featured Log",
			filters={
				"property": self.property_doc.name,
				"source": "API",
				"event_type": "Activated",
			},
			pluck="name",
		)
		self.assertEqual(len(logs), 1)
