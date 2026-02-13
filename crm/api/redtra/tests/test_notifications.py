
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import appointments, utils
from frappe.utils import add_days, get_datetime
from unittest.mock import patch

class TestAppointmentNotifications(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.mock_update_global_search = self.patcher.start()

		# Ensure schema is up to date
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_appointment", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_agency", force=True)

		frappe.set_user("Administrator")
		frappe.db.delete("CRM Notification")
		frappe.db.delete("Property Appointment")

		# Create Agent
		self.agent_email = "notif_agent@example.com"
		if not frappe.db.exists("User", self.agent_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.agent_email, 
				"first_name": "Notif Agent",
				"roles": [{"role": "Agent"}]
			}).insert(ignore_permissions=True)
			
		if not frappe.db.exists("Agent", {"user": self.agent_email}):
			self.agent_doc = frappe.get_doc({
				"doctype": "Agent",
				"user": self.agent_email,
				"full_name": "Notif Agent",
				"status": "Verified",
				"email": self.agent_email,
				"phone": "+999999999",
				"dfd_registration_id": "TEST-12345",
				"availability_slots": [
					{"day_of_week": "Monday", "start_time": "09:00:00", "end_time": "18:00:00"}
				]
			}).insert(ignore_permissions=True)
		else:
			self.agent_doc = frappe.get_doc("Agent", {"user": self.agent_email})

		# Create Property
		self.property = frappe.get_doc({
			"doctype": "Property",
			"title": "Notif Property",
			"listing_type": "Buy",
			"property_type": "Apartment",
			"agent": self.agent_doc.name,
			"status": "Active",
			"price": 1000000,
			"currency": "AED"
		}).insert(ignore_permissions=True)

		# Create Customer
		self.customer_email = "notif_customer@example.com"
		if not frappe.db.exists("User", self.customer_email):
			frappe.get_doc({
				"doctype": "User", 
				"email": self.customer_email, 
				"first_name": "Notif Customer",
				"roles": [{"role": "Customer"}]
			}).insert(ignore_permissions=True)

		utils.ensure_customer_record(self.customer_email, "Notif Customer", self.customer_email)
		self.customer_doc = utils.get_customer_by_user(self.customer_email)

	def tearDown(self):
		self.patcher.stop()

	def test_duplicate_notification_on_create(self):
		# Login as Customer
		frappe.set_user(self.customer_email)
		
		# Generate token for auth (if needed by API, but we call function directly)
		# appointments.create_appointment uses utils.get_current_user() so we just need frappe.set_user
		
		# Setup Mock Request
		# Need valid future Monday
		today = get_datetime()
		days_ahead = 0
		while add_days(today, days_ahead).strftime("%A") != "Monday":
			days_ahead += 1
		# Ensure at least 1 day ahead to avoid 'past' issues if logic exists
		if days_ahead == 0: days_ahead = 7
		
		target_date = add_days(today, days_ahead)
		start_time = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
		end_time = target_date.replace(hour=10, minute=30, second=0, microsecond=0)

		# Mock utils.get_mandate_agent_verification to False to simplify
		with patch("crm.api.redtra.utils.get_mandate_agent_verification", return_value=False):
			# Generate token
			token = utils.generate_jwt(self.customer_email)
			headers = {"Authorization": f"Bearer {token}"}

			# Mock Request
			class MockRequest:
				def __init__(self, data, headers):
					self.json = data
					self.method = "POST"
					self.headers = headers or {}
				def get_json(self): return self.json

			frappe.local.request = MockRequest({
				"property_id": self.property.name,
				"start_datetime": str(start_time),
				"end_datetime": str(end_time),
				"notes": "Testing notifications"
			}, headers)

			# Create Appointment
			appt = appointments.create_appointment()
			
			# Check Notifications
			# Should be 2 (1 for customer, 1 for agent) "Booked"
			# Should NOT have "Rescheduled"
			
			notifs = frappe.get_all("CRM Notification", fields=["notification_text", "to_user"])
			
			booked_count = sum(1 for n in notifs if "confirmed" in n.notification_text.lower() or "booked" in n.notification_text.lower())
			rescheduled_count = sum(1 for n in notifs if "rescheduled" in n.notification_text.lower())
			
			self.assertEqual(rescheduled_count, 0, f"Found {rescheduled_count} rescheduled notifications: {[n.notification_text for n in notifs]}")
			self.assertEqual(booked_count, 2, "Should be 2 booked notifications")

	def test_customer_visibility(self):
		# Create appointment with verified agent
		target_date = add_days(get_datetime(), 2)
		start_time = target_date.replace(hour=11, minute=0, second=0, microsecond=0)
		end_time = target_date.replace(hour=11, minute=30, second=0, microsecond=0)
		
		# Ensure agent is verified for validation
		frappe.db.set_value("Agent", self.agent_doc.name, "status", "Verified")

		appt = frappe.get_doc({
			"doctype": "Property Appointment",
			"customer": self.customer_doc.name,
			"agent": self.agent_doc.name,
			"property": self.property.name,
			"start_datetime": start_time,
			"end_datetime": end_time,
			"status": "Scheduled"
		}).insert(ignore_permissions=True)

		# Login as Customer
		frappe.set_user(self.customer_email)
		
		# Generate token
		token = utils.generate_jwt(self.customer_email)
		headers = {"Authorization": f"Bearer {token}"}
		
		# Call list_appointments
		# Mock request for empty filters
		class MockRequest:
			def __init__(self, headers):
				self.args = {}
				self.headers = headers
			def get_json(self): return {}
		
		frappe.local.request = MockRequest(headers)
		frappe.form_dict = frappe._dict({}) # For get_paginated_list if it used it, but list_appointments uses get_all directly
		
		# The API is list_appointments()
		appt_list = appointments.list_appointments()
		
		
		self.assertTrue(len(appt_list) > 0, "Customer should see their appointment")
		self.assertEqual(appt_list[0]["id"], appt.name)

	def test_customer_role_assignment(self):
		# Create a new user email who doesn't exist
		new_email = "new_customer_role_test@example.com"
		# Cleanup from previous runs
		if frappe.db.exists("Customer", {"email": new_email}):
			name = frappe.db.get_value("Customer", {"email": new_email}, "name")
			frappe.delete_doc("Customer", name, force=True)
		if frappe.db.exists("User", new_email):
			frappe.delete_doc("User", new_email, force=True)

		# Call create_customer API (via direct function call but mocking request)
		# We need a token for an EXISTING user (admin or agent) to call create_customer?
		# Wait, create_customer usually requires auth?
		# @utils.require_jwt() is present.
		# So a logged in user creates a customer profile?
		# Or maybe the user signs up?
		# If the user is signing up, who calls create_customer?
		# If it's an admin creating a customer, then okay.
		# If it's the USER creating their own profile, they need a token first (which implies they are a User).
		
		# Let's assume an Agent creates a Customer, or the User registers (and gets a token).
		# If a User exists but has no role, prompt them to create profile?
		
		# Test: Admin creates a customer with new email.
		frappe.set_user("Administrator")
		# Generate admin token
		admin_token = utils.generate_jwt("Administrator")
		headers = {"Authorization": f"Bearer {admin_token}"}
		
		class MockRequest:
			def __init__(self, data, headers):
				self.json = data
				self.method = "POST"
				self.headers = headers
			def get_json(self): return self.json

		frappe.local.request = MockRequest({
			"full_name": "New Role User",
			"email": new_email,
			"phone": "+1234567890"
		}, headers)
		
		from crm.api.redtra import customers
		customers.create_customer()
		
		# Check if User was created and has role
		user_name = frappe.db.get_value("User", {"email": new_email}, "name")
		self.assertTrue(user_name, "User should be created")
		roles = frappe.get_roles(user_name)
		self.assertIn("Customer", roles, "User should have Customer role")

