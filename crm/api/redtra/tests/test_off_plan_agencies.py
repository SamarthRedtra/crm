
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import agencies, reviews

class TestOffPlanAgencies(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Fix Agency module if incorrect in test DB
		if frappe.db.exists("DocType", "Agency"):
			frappe.db.sql("UPDATE `tabDocType` SET module='FCRM' WHERE name='Agency'")
			frappe.db.commit()
			frappe.clear_cache()
		
		suffix = frappe.generate_hash(length=8)
		
		# Create Agencies
		self.agency1 = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": f"_Agency_1_{suffix}_",
			"status": "Active"
		}).insert(ignore_permissions=True)
		
		self.agency2 = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": f"_Agency_2_{suffix}_",
			"status": "Active"
		}).insert(ignore_permissions=True)
		
		# Create Agent User
		self.agent_user_email = f"agent_{suffix}@example.com"
		if not frappe.db.exists("User", self.agent_user_email):
			frappe.get_doc({
				"doctype": "User",
				"email": self.agent_user_email,
				"first_name": "Test Agent",
				"send_welcome_email": 0,
				"roles": [{"role": "Agent"}]
			}).insert(ignore_permissions=True)

		# Create Agent for Agency 1
		self.agent1 = frappe.get_doc({
			"doctype": "Agent",
			"user": self.agent_user_email,
			"dfd_registration_id": f"DLD-{suffix}",
			"status": "Verified",
			"agency": self.agency1.name
		}).insert(ignore_permissions=True)
		
		# Create Customer for Review
		self.customer_user = f"customer_{suffix}@example.com"
		if not frappe.db.exists("User", self.customer_user):
			frappe.get_doc({
				"doctype": "User",
				"email": self.customer_user,
				"first_name": "Test Customer",
				"send_welcome_email": 0
			}).insert(ignore_permissions=True)
			
		self.customer = frappe.get_doc({
			"doctype": "Customer",
			"full_name": "Test Customer",
			"user": self.customer_user
		}).insert(ignore_permissions=True)

		# Create Off-Plan Property linked to Agency 2 via multi-select (and Agent 1 as owner)
		self.off_plan_prop = frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_OffPlan_{suffix}_",
			"status": "Active",
			"agent": self.agent1.name, # Owned by Agent 1 (Agency 1)
			"listing_type": "Off Plan",
			"property_type": "Apartment",
			"price": 2000000,
			"currency": "AED",
			"city": "Dubai",
			"off_plan_agencies": [
				{"agency": self.agency2.name} 
			]
		}).insert(ignore_permissions=True)
		
		# Create Normal Active Property for Agency 1
		self.normal_prop = frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Normal_{suffix}_",
			"status": "Active",
			"agent": self.agent1.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"currency": "AED",
			"city": "Dubai"
		}).insert(ignore_permissions=True)
		
		# Create Sold Property (Inactive for totals) for Agency 1
		self.sold_prop = frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Sold_{suffix}_",
			"status": "Inactive",
			"is_sold": 1,
			"agent": self.agent1.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"currency": "AED",
			"city": "Dubai"
		}).insert(ignore_permissions=True)

		frappe.db.commit()

	def test_agency_listings_count_fix(self):
		"""Verify total_listings matches active properties count (Fix for original issue)"""
		details = agencies.get_agency(self.agency1.name)
		
		# Agency 1 has:
		# 1 Active Normal Property (Agent 1)
		# 1 Active Off-Plan Property (Agent 1)
		# 1 Sold Property (Agent 1)
		
		# total_listings should only count Active properties = 2
		# properties list should contain 2 items
		
		self.assertEqual(details["total_listings"], 2, "Total listings should only count Active properties")
		self.assertEqual(len(details["properties"]), 2, "Properties list should contain 2 active properties")
		
		# Verify Sold property is NOT in the list
		prop_ids = [p["id"] for p in details["properties"]]
		self.assertNotIn(self.sold_prop.name, prop_ids)

	def test_off_plan_agency_linking(self):
		"""Verify Agency 2 sees the Off-Plan property linked via multi-select"""
		details = agencies.get_agency(self.agency2.name)
		
		# Agency 2 has:
		# 0 Agents
		# 1 Off-Plan Property linked via off_plan_agencies
		
		self.assertEqual(details["total_listings"], 1, "Agency 2 should show 1 active listing")
		self.assertEqual(len(details["properties"]), 1, "Agency 2 should list 1 property")
		self.assertEqual(details["properties"][0]["id"], self.off_plan_prop.name)
		
		# Verify list_agency_properties also returns it
		list_res = agencies.list_agency_properties(self.agency2.name)
		self.assertEqual(list_res["total_items"], 1)
		self.assertEqual(list_res["items"][0]["id"], self.off_plan_prop.name)

		# Verify get_property returns off_plan_agencies
		from crm.api.redtra import properties
		prop_detail = properties.get_property(self.off_plan_prop.name)
		self.assertIn("off_plan_agencies", prop_detail)
		self.assertEqual(len(prop_detail["off_plan_agencies"]), 1)
		self.assertEqual(prop_detail["off_plan_agencies"][0]["id"], self.agency2.name)

	def test_review_reviewer_name(self):
		"""Verify reviewer_name is present in get_property_reviews"""
		# Create a review
		review = frappe.get_doc({
			"doctype": "Review and Rating",
			"property": self.normal_prop.name,
			"customer": self.customer.name,
			"overall_rating": 5,
			"status": "Submitted"
		}).insert(ignore_permissions=True)
		
		# Call API
		res = reviews.get_property_reviews(self.normal_prop.name)
		
		self.assertTrue(len(res["items"]) > 0)
		review_item = res["items"][0]
		self.assertEqual(review_item["reviewer_name"], "Test Customer")
		
