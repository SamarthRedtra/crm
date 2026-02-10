
import frappe
from frappe.tests import IntegrationTestCase
from crm.api.redtra import agencies

class TestAgencyCounts(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=8)
		
		# Create Agency
		self.agency = frappe.get_doc({
			"doctype": "Agency",
			"agency_name": f"_Agency_Count_Test_{suffix}_",
			"status": "Active"
		}).insert(ignore_permissions=True)
		
		# Create Agent
		self.agent = frappe.get_doc({
			"doctype": "Agent",
			"full_name": f"_Agent_Count_Test_{suffix}_",
			"status": "Verified",
			"agency": self.agency.name
		}).insert(ignore_permissions=True)
		
		# Create Active Property
		frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Active_{suffix}_",
			"status": "Active",
			"agent": self.agent.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"city": "Dubai"
		}).insert(ignore_permissions=True)
		
		# Create Inactive Property (e.g., Sold)
		frappe.get_doc({
			"doctype": "Property",
			"title": f"_Prop_Sold_{suffix}_",
			"status": "Sold",
			"agent": self.agent.name,
			"listing_type": "Buy",
			"property_type": "Apartment",
			"price": 1000000,
			"city": "Dubai"
		}).insert(ignore_permissions=True)
		
		frappe.db.commit()

	def test_agency_listings_count(self):
		# Verify discrepancy
		details = agencies.get_agency(self.agency.name)
		
		# Current behavior: total_listings counts ALL (2), properties list contains only Active (1)
		self.assertEqual(details["total_listings"], 2, "Total listings should include inactive ones currently")
		self.assertEqual(len(details["properties"]), 1, "Properties list should only include active ones")
		
		# After fix, total_listings should match properties count (1)
		# self.assertEqual(details["total_listings"], len(details["properties"]))

