
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import customers, utils, favorites, appointments
from frappe.utils import add_days, get_datetime
from unittest.mock import patch

class TestGetCustomerDetails(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		# Ensure schema is up to date
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_appointment", force=True)
		frappe.reload_doc("fcrm", "doctype", "favorite_property", force=True)
		frappe.reload_doc("fcrm", "doctype", "customer", force=True)

		frappe.set_user("Administrator")
		# Cleanup
		frappe.db.delete("Property Appointment")
		frappe.db.delete("Favorite Property")
		
		# Create Agent
		self.agent_email = "details_agent@example.com"
		if not frappe.db.exists("User", self.agent_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.agent_email, 
				"first_name": "Details Agent",
				"roles": [{"role": "Agent"}]
			}).insert(ignore_permissions=True)
			
		if not frappe.db.exists("Agent", {"user": self.agent_email}):
			self.agent_doc = frappe.get_doc({
				"doctype": "Agent",
				"user": self.agent_email,
				"full_name": "Details Agent",
				"status": "Verified",
				"dfd_registration_id": "DET-123",
				"availability_slots": [
					{"day_of_week": "Monday", "start_time": "09:00:00", "end_time": "18:00:00"}
				]
			}).insert(ignore_permissions=True)
		else:
			self.agent_doc = frappe.get_doc("Agent", {"user": self.agent_email})

		# Create Property
		self.property = frappe.get_doc({
			"doctype": "Property",
			"title": "Details Property",
			"listing_type": "Buy",
			"property_type": "Apartment",
			"agent": self.agent_doc.name,
			"status": "Active",
			"price": 600000,
			"currency": "AED"
		}).insert(ignore_permissions=True)

		# Create Customer User
		self.customer_email = "details_customer@example.com"
		if not frappe.db.exists("User", self.customer_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.customer_email, 
				"first_name": "Details Customer",
				"roles": [{"role": "Customer"}]
			}).insert(ignore_permissions=True)
			
		utils.ensure_customer_record(self.customer_email, "Details Customer", self.customer_email)
		self.customer_doc = utils.get_customer_by_user(self.customer_email)

	def tearDown(self):
		self.patcher.stop()

	def test_get_customer_includes_details(self):
		# Setup Data: Favorite and Appointment
		
		# 1. Add Favorite (as Customer)
		frappe.set_user(self.customer_email)
		doc = frappe.get_doc({
			"doctype": "Favorite Property",
			"user": self.customer_email,
			"property": self.property.name
		}).insert(ignore_permissions=True)
		
		# 2. Create Appointment
		# Find next Monday
		today = get_datetime()
		days_ahead = 0
		while add_days(today, days_ahead).strftime("%A") != "Monday":
			days_ahead += 1
		if days_ahead == 0: days_ahead = 7
		
		target_date = add_days(today, days_ahead)
		start_time = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
		end_time = target_date.replace(hour=10, minute=30, second=0, microsecond=0)
		
		fixture = frappe.get_doc({
			"doctype": "Property Appointment",
			"customer": self.customer_doc.name,
			"agent": self.agent_doc.name,
			"property": self.property.name,
			"start_datetime": start_time,
			"end_datetime": end_time,
			"status": "Scheduled"
		}).insert(ignore_permissions=True)
		
		# 3. Call get_customer as Administrator (or Agent)
		frappe.set_user("Administrator")
		# Mock Request
		class MockRequest:
			def __init__(self, headers):
				self.headers = headers
				self.method = "GET"
				self.args = {}
			def get_json(self): return {}

		# Generate Token for Administrator? Or just mock headers if using require_jwt
		# require_jwt checks Authorization header.
		token = utils.generate_jwt("Administrator")
		headers = {"Authorization": f"Bearer {token}"}
		frappe.local.request = MockRequest(headers)
		
		# Call API
		response = customers.get_customer(self.customer_doc.name)
		
		# Assertions
		self.assertIn("favorites", response)
		self.assertIn("appointments", response)
		
		self.assertEqual(len(response["favorites"]), 1)
		self.assertEqual(response["favorites"][0]["property"]["id"], self.property.name)
		
		self.assertEqual(len(response["appointments"]), 1)
		self.assertEqual(response["appointments"][0]["id"], fixture.name)
