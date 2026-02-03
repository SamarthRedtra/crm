
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import agencies, auth, utils

class TestAPIEnhancements(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=8)
		
		# Create Area
		self.area = frappe.get_doc({
			"doctype": "Area",
			"area_name": f"_Area_{suffix}_",
			"city": "Dubai"
		}).insert(ignore_permissions=True)
		
		# Create Agency
		self.agency = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": f"_Agency_{suffix}_",
			"status": "Active"
		}).insert(ignore_permissions=True)
		
		# Create Agent User
		self.agent_user_email = f"agent_{suffix}@example.com"
		if not frappe.db.exists("User", self.agent_user_email):
			frappe.get_doc({
				"doctype": "User",
				"email": self.agent_user_email,
				"first_name": f"Agent {suffix}",
				"send_welcome_email": 0
			}).insert(ignore_permissions=True)
		
		# Create Agent
		self.agent = frappe.get_doc({
			"doctype": "Agent",
			"full_name": f"_Agent_{suffix}_",
			"status": "Verified",
			"user": self.agent_user_email,
			"agency": self.agency.name
		}).insert(ignore_permissions=True)
		
		# Create Properties
		# 1. Sale
		frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Sale_{suffix}_",
			"status": "Active",
			"agent": self.agent.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"area": self.area.name
		}).insert(ignore_permissions=True)
		
		# 2. Rent
		frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Rent_{suffix}_",
			"status": "Active",
			"agent": self.agent.name,
			"listing_type": "Rent",
			"property_type": "Apartment",
			"price": 5000,
			"area": self.area.name
		}).insert(ignore_permissions=True)
		
		frappe.db.commit()

	def test_agency_service_areas_name(self):
		# Verify get_agency returns area name instead of ID
		details = agencies.get_agency(self.agency.name)
		self.assertIn(self.area.area_name, details["service_areas"])
		self.assertNotIn(self.area.name, details["service_areas"])

	def test_agent_profile_agency_stats(self):
		# Verify auth._build_agent_profile includes agency stats
		user_doc = frappe.get_doc("User", self.agent_user_email)
		start_of_day, end_of_day = auth._current_day_bounds()
		
		profile = auth._build_agent_profile(user_doc, self.agent, start_of_day, end_of_day)
		
		agency = profile.get("agency")
		self.assertIsNotNone(agency)
		self.assertEqual(agency["name"], self.agency.agency_name)
		self.assertEqual(agency.get("total_listings"), 2)
		self.assertEqual(agency.get("active_listings"), 2)
		self.assertEqual(agency.get("sale_listings"), 1)
		self.assertEqual(agency.get("rent_listings"), 1)

def run_tests():
	# Helper for console execution
	test_suite = TestAPIEnhancements()
	test_suite.setUp()
	try:
		print("Running test_agency_service_areas_name...")
		test_suite.test_agency_service_areas_name()
		print("test_agency_service_areas_name passed!")
		
		print("Running test_agent_profile_agency_stats...")
		test_suite.test_agent_profile_agency_stats()
		print("test_agent_profile_agency_stats passed!")
	finally:
		# Use default tearDown if any
		pass
