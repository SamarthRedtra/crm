
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import agencies, reviews
from crm.fcrm.doctype.agency.agency import Agency

class TestNewAPIs(IntegrationTestCase):
	def setUp(self):
		# Create test user/customer if needed
		frappe.db.delete("Agency", {"agency_name": "_Test Agency_"})
		frappe.db.delete("Agent", {"full_name": "_Test Agent_"})
		frappe.db.delete("Review and Rating", {"review_text": "_Test Review_"})
		frappe.db.delete("CRM Lead", {"first_name": "_Test Lead_"})
		
		# Force fix broken module reference in DB if any
		frappe.db.sql("UPDATE `tabDocType` SET module='FCRM' WHERE name='Review and Rating'")
		frappe.db.commit()
		
		try:
			frappe.reload_doc("fcrm", "doctype", "review_and_rating")
		except ImportError:
			pass
		
		# Create a unique test customer user
		import random
		self.suffix = str(random.randint(1000, 9999))
		self.user = f"test_customer_{self.suffix}@example.com"
		
		if not frappe.db.exists("User", self.user):
			user = frappe.new_doc("User")
			user.email = self.user
			user.first_name = "Test Customer"
			user.save(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", self.user)
			
		name = frappe.db.exists("Customer", self.user)
		if not name:
			customer = frappe.new_doc("Customer")
			customer.name = self.user # Explicitly set name if autoname uses field:email usually or manually
			customer.customer_name = f"Test Customer {self.suffix}"
			# customer.email_id = self.user # Removed as it causes error
			customer.user = user.name
			customer.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		# frappe.db.rollback() 

	def test_agency_apis(self):
		frappe.set_user("Administrator")
		
		# 1. Create Agency
		agency_doc = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": "_Test Agency_",
			"status": "Active",
			"email": "test@agency.com"
		}).insert(ignore_permissions=True)
		
		# 2. Get Agency (Public API)
		frappe.set_user("Guest")
		details = agencies.get_agency(agency_doc.name)
		self.assertEqual(details["name"], "_Test Agency_")
		
		# 3. List Agencies
		listing = agencies.list_agencies()
		self.assertTrue(any(a["name"] == "_Test Agency_" for a in listing["items"]))

	def test_review_apis(self):
		# Setup: Create Agent
		frappe.set_user("Administrator")
		# Create user for agent
		agent_email = f"agent_{self.suffix}@example.com"
		if not frappe.db.exists("User", agent_email):
			frappe.get_doc({
				"doctype": "User",
				"email": agent_email,
				"first_name": "Test Agent User",
				"send_welcome_email": 0
			}).insert(ignore_permissions=True)

		agent = frappe.get_doc({
			"doctype": "Agent",
			"full_name": f"_Test Agent {self.suffix}_",
			"status": "Verified",
			"phone": "+1234567890",
			"dfd_registration_id": f"DLD-{self.suffix}",
			"user": agent_email
		}).insert(ignore_permissions=True)
		agent_id = agent.name

		# 1. Submit Agent Review
		frappe.set_user(self.user)
		original_get_request_json = reviews.utils.get_request_json
		try:
			reviews.utils.get_request_json = lambda required_fields=None: {
				"overall_rating": 5,
				"agent_rating": 4,
				"review_text": "_Test Review_",
			}
			frappe.local.redtra_auth = {"payload": {"user": self.user}}
			submitted = reviews._submit_general_review(agent_id=agent_id)
		finally:
			reviews.utils.get_request_json = original_get_request_json
			if hasattr(frappe.local, "redtra_auth"):
				delattr(frappe.local, "redtra_auth")

		self.assertEqual(submitted["overall_rating"], 5.0)
		self.assertEqual(submitted["agent_rating"], 4.0)
		self.assertEqual(submitted["review_text"], "_Test Review_")

		# 2. List Agent Reviews
		frappe.set_user("Guest")
		result = reviews.get_agent_reviews(agent_id)
		
		self.assertEqual(result["ratings"]["total_reviews"], 1)
		self.assertEqual(result["items"][0]["review_text"], "_Test Review_")
		self.assertEqual(result["items"][0]["overall_rating"], 5.0)
		self.assertEqual(result["items"][0]["agent_rating"], 4.0)
		self.assertEqual(result["ratings"]["average_overall_rating"], 5.0)
		self.assertEqual(result["ratings"]["average_agent_rating"], 4.0)

	def test_property_review_apis(self):
		# Setup: Create Property
		frappe.set_user("Administrator")
		# Ensure dependencies exist
		area = frappe.get_doc({"doctype": "Area", "area_name": "_Test Area_", "city": "Dubai"}).insert(ignore_permissions=True) if not frappe.db.exists("Area", "_Test Area_") else frappe.get_doc("Area", "_Test Area_")
		developer = frappe.get_doc({"doctype": "Developer", "developer_name": "_Test Dev_"}).insert(ignore_permissions=True) if not frappe.db.exists("Developer", "_Test Dev_") else frappe.get_doc("Developer", "_Test Dev_")
		
		agent_prop_email = f"agent_prop_{self.suffix}@example.com"
		if not frappe.db.exists("User", agent_prop_email):
			frappe.get_doc({
				"doctype": "User",
				"email": agent_prop_email,
				"first_name": "Test Agent Prop",
				"send_welcome_email": 0
			}).insert(ignore_permissions=True)

		agent = frappe.get_doc({
			"doctype": "Agent",
			"full_name": f"_Test Agent Prop {self.suffix}_",
			"status": "Verified",
			"phone": "+1234567891",
			"dfd_registration_id": f"DLD-PROP-{self.suffix}",
			"user": agent_prop_email
		}).insert(ignore_permissions=True)
		
		property_doc = frappe.get_doc({
			"doctype": "Property",
			"title": "_Test Property_",
			"status": "Active",
			"area": area.name,
			"developer": developer.name,
			"agent": agent.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"currency": "AED",
		}).insert(ignore_permissions=True)
		property_id = property_doc.name

		# 1. Create Property Review directly
		frappe.get_doc({
			"doctype": "Review and Rating",
			"property": property_id,
			"customer": self.user,
			"status": "Published",
			"overall_rating": 0.9,
			"property_rating": 1,
			"review_text": "_Test Property Review_"
		}).insert(ignore_permissions=True)

		# 2. Get Property Reviews (Public)
		frappe.set_user("Guest")
		result = reviews.get_property_reviews(property_id)
		
		self.assertEqual(result["ratings"]["total_reviews"], 1)
		self.assertEqual(result["items"][0]["review_text"], "_Test Property Review_")
		self.assertEqual(result["items"][0]["overall_rating"], 4.5)
		self.assertEqual(result["items"][0]["property_rating"], 5.0)
		self.assertEqual(result["ratings"]["average_overall_rating"], 4.5)
		self.assertEqual(result["ratings"]["average_property_rating"], 5.0)

	def test_serialize_review_returns_five_point_scale(self):
		frappe.set_user("Administrator")

		review = frappe.get_doc({
			"doctype": "Review and Rating",
			"customer": self.user,
			"status": "Submitted",
			"overall_rating": 0.6,
			"agent_rating": 0.8,
			"property_rating": 1,
			"review_text": "_Serialized Review_"
		}).insert(ignore_permissions=True)

		result = reviews.serialize_review(review.name)

		self.assertEqual(result["overall_rating"], 3.0)
		self.assertEqual(result["agent_rating"], 4.0)
		self.assertEqual(result["property_rating"], 5.0)
		self.assertEqual(result["review_text"], "_Serialized Review_")


	def test_crm_lead_creation(self):
		frappe.set_user("Administrator")
		
		# Create dependencies
		agency = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": "_Test Agency_",
			"status": "Active"
		}).insert(ignore_permissions=True)
		
		agent_lead_email = f"agent_lead_{self.suffix}@example.com"
		if not frappe.db.exists("User", agent_lead_email):
			frappe.get_doc({
				"doctype": "User",
				"email": agent_lead_email,
				"first_name": "Test Agent Lead",
				"send_welcome_email": 0
			}).insert(ignore_permissions=True)

		agent = frappe.get_doc({
			"doctype": "Agent",
			"full_name": f"_Test Agent Lead {self.suffix}_",
			"agency": agency.name,
			"dfd_registration_id": f"DLD-LEAD-{self.suffix}",
			"user": agent_lead_email
		}).insert(ignore_permissions=True)
		
		# Create CRM Lead
		lead = frappe.get_doc({
			"doctype": "CRM Lead",
			"first_name": "_Test Lead_",
			"agent_id": agent.name,
			"agency": agency.name
		}).insert(ignore_permissions=True)
		
		# Verify Linkage
		retrieved_lead = frappe.get_doc("CRM Lead", lead.name)
		self.assertEqual(retrieved_lead.agent_id, agent.name)
		self.assertEqual(retrieved_lead.agency, agency.name)

