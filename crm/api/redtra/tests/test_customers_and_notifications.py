
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import customers, notifications, utils
from unittest.mock import patch

class TestCustomersAndNotifications(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		frappe.set_user("Administrator")
		# Create a dummy user for testing
		self.test_email = "test_customer@example.com"
		if not frappe.db.exists("User", self.test_email):
			user = frappe.get_doc({
				"doctype": "User",
				"email": self.test_email,
				"first_name": "Test Customer",
				"send_welcome_email": 0,
				"roles": [{"role": "Customer"}]
			}).insert(ignore_permissions=True)

	def tearDown(self):
		self.patcher.stop()
		frappe.set_user("Administrator")
		# Cleanup
		if frappe.db.exists("Customer", {"email": self.test_email}):
			frappe.db.delete("Customer", {"email": self.test_email})
		
		# Delete notifications created during test
		frappe.db.delete("CRM Notification", {"to_user": "Administrator"})

	def test_customer_crud(self):
		# Generate token
		token = utils.generate_jwt(self.test_email)
		headers = {"Authorization": f"Bearer {token}"}

		# 1. Create Customer
		frappe.form_dict = frappe._dict({
			"full_name": "Test Customer",
			"email": self.test_email,
			"phone": "+1234567890",
			"preferred_city": "Dubai"
		})
		
		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "POST"
				self.headers = headers or {}
			
			def get_json(self):
				return self.json
		
		frappe.local.request = MockRequest({
			"full_name": "Test Customer",
			"email": self.test_email,
			"phone": "+1234567890",
			"preferred_city": "Dubai"
		}, headers)

		created_customer = customers.create_customer()
		self.assertEqual(created_customer["full_name"], "Test Customer")
		self.assertEqual(created_customer["email"], self.test_email)
		customer_id = created_customer["id"]

		# 2. Get Customer
		frappe.local.request = MockRequest({}, headers)
		get_result = customers.get_customer(customer_id)
		self.assertEqual(get_result["id"], customer_id)

		# 3. List Customers
		frappe.form_dict = frappe._dict({"search": "Test Customer"})
		frappe.local.request = MockRequest({}, headers)
		list_result = customers.list_customers()
		self.assertGreaterEqual(len(list_result["items"]), 1)
		found = False
		for item in list_result["items"]:
			if item["id"] == customer_id:
				found = True
				break
		self.assertTrue(found)

		# 4. Update Customer
		frappe.local.request = MockRequest({
			"phone": "+9876543210"
		}, headers)
		updated_customer = customers.update_customer(customer_id)
		self.assertEqual(updated_customer["phone"], "+9876543210")

		# 5. Delete Customer
		frappe.local.request = MockRequest({}, headers)
		delete_result = customers.delete_customer(customer_id)
		self.assertEqual(delete_result["message"], "Customer deleted successfully")
		
		with self.assertRaises(frappe.DoesNotExistError):
			customers.get_customer(customer_id)

	def test_delete_notification(self):
		# Generate token
		token = utils.generate_jwt("Administrator")
		headers = {"Authorization": f"Bearer {token}"}
		
		# Create a notification
		notification = frappe.get_doc({
			"doctype": "CRM Notification",
			"to_user": "Administrator",
			"notification_text": "Test Notification",
			"read": 0
		}).insert()

		notification_id = notification.name
		
		# Verify it exists
		self.assertTrue(frappe.db.exists("CRM Notification", notification_id))

		class MockRequest:
			def __init__(self, data, headers=None):
				self.json = data
				self.method = "DELETE"
				self.headers = headers or {}
			
			def get_json(self):
				return self.json

		# Delete it
		frappe.local.request = MockRequest({}, headers)
		notifications.delete_notification(notification_id)
		
		# Verify it's gone
		self.assertFalse(frappe.db.exists("CRM Notification", notification_id))

		# Try to delete again, should fail
		with self.assertRaises(frappe.DoesNotExistError):
			notifications.delete_notification(notification_id)
