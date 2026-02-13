
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import transactions, properties, utils
from unittest.mock import patch

class TestTransactions(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		# Ensure schema is up to date for modified/new doctypes
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_transaction_log", force=True)
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
			"transaction_type": "Sale",
			"amount": 1000000,
			"currency": "AED",
			"notes": "Sold!"
		}, headers)

		# Create Transaction
		txn = transactions.create_transaction()
		
		# Verify Transaction created
		self.assertTrue(txn["id"])
		self.assertEqual(txn["property"], self.property_doc.name)
		self.assertEqual(txn["transaction_type"], "Sale")

		# Verify Property is_sold = 1
		prop = frappe.get_doc("Property", self.property_doc.name)
		self.assertEqual(prop.is_sold, 1)

		# Verify List Transactions
		frappe.local.request = MockRequest({}, headers)
		# list_transactions reads frappe.form_dict usually for params, but default checks usually pass if empty
		# We should mock form_dict if needed, but list_transactions uses get("page") etc which are fine as None
		txn_list = transactions.list_transactions()
		# Depending on test isolation, we might have other transactions, but ours should be there
		found = False
		for item in txn_list["items"]:
			if item["id"] == txn["id"]:
				found = True
				break
		self.assertTrue(found)

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
