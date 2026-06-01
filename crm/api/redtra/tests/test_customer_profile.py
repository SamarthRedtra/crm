
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import auth, utils, properties, favorites, appointments
from frappe.utils import add_days, get_datetime
from unittest.mock import patch

class TestCustomerProfile(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		# Ensure schema is up to date
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_appointment", force=True)
		frappe.reload_doc("fcrm", "doctype", "favorite_property", force=True)

		frappe.set_user("Administrator")
		# Cleanup
		frappe.db.delete("Property Appointment")
		frappe.db.delete("Favorite Property")
		
		# Create Agent
		self.agent_email = "profile_agent@example.com"
		if not frappe.db.exists("User", self.agent_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.agent_email, 
				"first_name": "Profile Agent",
				"roles": [{"role": "Agent"}]
			}).insert(ignore_permissions=True)
		
		if not frappe.db.exists("Agent", {"user": self.agent_email}):
			self.agent_doc = frappe.get_doc({
				"doctype": "Agent",
				"user": self.agent_email,
				"full_name": "Profile Agent",
				"status": "Verified",
				"dfd_registration_id": "PROF-123",
				"phone": "+971500001111",
				"whatsapp_number": "+971500001111",
				"availability_slots": [
					{"day_of_week": "Monday", "start_time": "09:00:00", "end_time": "18:00:00"}
				]
			}).insert(ignore_permissions=True)
		else:
			self.agent_doc = frappe.get_doc("Agent", {"user": self.agent_email})

		# Create Property
		self.property = frappe.get_doc({
			"doctype": "Property",
			"title": "Profile Property",
			"listing_type": "Buy",
			"property_type": "Apartment",
			"agent": self.agent_doc.name,
			"status": "Active",
			"price": 500000,
			"currency": "AED"
		}).insert(ignore_permissions=True)

		# Create Customer User
		self.customer_email = "profile_customer@example.com"
		if not frappe.db.exists("User", self.customer_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.customer_email, 
				"first_name": "Profile Customer",
				"roles": [{"role": "Customer"}]
			}).insert(ignore_permissions=True)
			
		utils.ensure_customer_record(self.customer_email, "Profile Customer", self.customer_email)
		# Ensure role
		if "Customer" not in frappe.get_roles(self.customer_email):
			u = frappe.get_doc("User", self.customer_email)
			u.add_roles("Customer")
			
		self.customer_doc = utils.get_customer_by_user(self.customer_email)

	def tearDown(self):
		self.patcher.stop()

	def test_customer_profile_includes_favorites_and_appointments(self):
		# Login as Customer
		frappe.set_user(self.customer_email)
		
		# Generate Token
		token = utils.generate_jwt(self.customer_email)
		headers = {"Authorization": f"Bearer {token}"}
		
		# 1. Add Favorite
		# Mock Request for add_favorite
		class MockRequest:
			def __init__(self, data, headers):
				self.json = data
				self.method = "POST"
				self.headers = headers
			def get_json(self): return self.json

		with patch("crm.api.redtra.utils.extract_bearer_token", return_value="fake"), patch(
			"crm.api.redtra.utils.decode_jwt", return_value={"user": self.customer_email}
		):
			frappe.local.request = MockRequest({"property_id": self.property.name}, headers)
			favorites.add_favorite() # This calls get_current_user -> checks token
			
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
			
			# We can use create_appointment API or just insert doc
			# API is better to test integration but requires mocking request again
			frappe.local.request = MockRequest({
				"property_id": self.property.name,
				"start_datetime": str(start_time),
				"end_datetime": str(end_time),
				"notes": "Profile Test"
			}, headers)
			
			# Mock agent verification mandatory check
			with patch("crm.api.redtra.utils.get_mandate_agent_verification", return_value=False):
				appointments.create_appointment()
				
			# 3. Call get_profile
			# Mock request for get_profile (GET, no data)
			frappe.local.request = MockRequest({}, headers)
			
			profile = auth.get_profile()
		
		# Assertions
		self.assertIn("favorites", profile)
		self.assertIn("appointments", profile)
		
		self.assertEqual(len(profile["favorites"]), 1)
		self.assertEqual(profile["favorites"][0]["property"]["id"], self.property.name)
		
		self.assertEqual(len(profile["appointments"]), 1)
		self.assertEqual(profile["appointments"][0]["property"]["id"], self.property.name)
		self.assertEqual(profile["appointments"][0]["status"], "Scheduled")
