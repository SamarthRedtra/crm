import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch

from crm.api.redtra import properties


class TestTrakheesiIntegration(IntegrationTestCase):
	def setUp(self):
		self.patcher = patch("frappe.model.document.update_global_search")
		self.patcher.start()
		frappe.set_user("Administrator")
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "fcrm_settings", force=True)

		settings = frappe.get_single("FCRM Settings")
		settings.trakheesi_validation_base_url = "https://example.com/permit/validate/listing/v7"
		settings.trakheesi_delist_base_url = "https://example.com/permit/listing/delist/v1"
		settings.trakheesi_request_timeout_seconds = 10
		settings.trakheesi_authorization_key = "test-key"
		settings.save(ignore_permissions=True)

		self.agent_email = "trakheesi_agent_test@example.com"
		if not frappe.db.exists("User", self.agent_email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": self.agent_email,
					"first_name": "Trakheesi Agent",
					"send_welcome_email": 0,
					"roles": [{"role": "Agent"}],
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Agent", {"user": self.agent_email}):
			self.agent = frappe.get_doc(
				{
					"doctype": "Agent",
					"user": self.agent_email,
					"full_name": "Trakheesi Agent",
					"phone": "+971500000111",
					"whatsapp_number": "+971500000111",
					"status": "Verified",
					"dfd_registration_id": "TRAKHEESI-AGENT-001",
					"email": self.agent_email,
				}
			).insert(ignore_permissions=True)
		else:
			self.agent = frappe.get_doc("Agent", {"user": self.agent_email})

	def tearDown(self):
		self.patcher.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _set_request_payload(self, payload: dict):
		class MockRequest:
			def __init__(self, data):
				self.json = data
				self.method = "POST"
				self.headers = {}

			def get_json(self):
				return self.json

		frappe.local.request = MockRequest(payload)

	def test_create_property_blocks_when_verification_fails(self):
		self._set_request_payload(
			{
				"title": "Trakheesi Invalid",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1500000,
				"currency": "AED",
				"trakheesi_permit_number": "P-001",
				"trakheesi_qr_code": "/files/qr.png",
				"trakheesi_listing_number": "7123139000",
				"license_number": "723355",
			}
		)

		with patch("crm.api.redtra.utils.extract_bearer_token", return_value="fake"), patch(
			"crm.api.redtra.utils.decode_jwt",
			return_value={"user": self.agent_email},
		), patch(
			"crm.api.redtra.trakheesi.verify_listing",
			side_effect=frappe.ValidationError("listing not valid"),
		):
			with self.assertRaises(frappe.ValidationError):
				properties.create_property()

	def test_create_property_applies_non_price_sync_and_ignores_arabic(self):
		self._set_request_payload(
			{
				"title": "Trakheesi Valid",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 1500000,
				"currency": "AED",
				"trakheesi_permit_number": "P-002",
				"trakheesi_qr_code": "/files/qr2.png",
				"trakheesi_listing_number": "7123139000",
				"license_number": "723355",
				"zone_name": "",
				"city": "",
			}
		)

		mock_verification = {
			"listing_guid": "listing-guid-001",
			"validation_url": "https://validation.example/test",
			"verified_at": "2026-05-18 12:00:00",
			"property_size": 70.44,
			"zone_name_en": "Al Thanyah Third",
			"property_name_en": "SAMAR 3",
			"building_name_en": None,
			"building_name_en_fallback": "SAMAR 3 Building",
			"permit_location": "Dubai Marina",
			"rooms_count": "1",
			"room_type_en": "1 B/R",
			"floor_number": "1",
			"facilities": ["Balcony", {"facilityNameEn": "Shared Pool"}],
			"verification_payload": "{\"ok\":true}",
			"listing_type_en": "Rent",
			"property_name_ar": "سمر 3",
			"zone_name_ar": "الثنيه الثالثة",
		}

		with patch("crm.api.redtra.utils.extract_bearer_token", return_value="fake"), patch(
			"crm.api.redtra.utils.decode_jwt",
			return_value={"user": self.agent_email},
		), patch(
			"crm.api.redtra.trakheesi.verify_listing",
			return_value=mock_verification,
		):
			result = properties.create_property()

		doc = frappe.get_doc("Property", result["id"])
		self.assertEqual(doc.price, 1500000)
		self.assertEqual(doc.area_sqft, 70.44)
		self.assertEqual(doc.zone_name, "Al Thanyah Third")
		self.assertEqual(doc.city, "Dubai Marina")
		self.assertEqual(doc.address_line1, "SAMAR 3 Building")
		self.assertEqual(doc.address_line2, "Floor 1")
		self.assertEqual(doc.bedrooms, 1)
		self.assertCountEqual([row.amenity_name for row in doc.amenities], ["Balcony", "Shared Pool"])
		self.assertEqual(doc.trakheesi_listing_guid, "listing-guid-001")
		self.assertEqual(doc.trakheesi_validation_url, "https://validation.example/test")
		self.assertEqual(doc.trakheesi_listing_number, "7123139000")
		self.assertEqual(doc.license_number, "723355")
		self.assertEqual(doc.status, "Under Verification")

	def test_property_insert_as_administrator_still_verifies_trakheesi(self):
		mock_verification = {
			"listing_guid": "listing-guid-admin-001",
			"validation_url": "https://validation.example/admin",
			"verified_at": "2026-05-22 15:30:00",
			"property_size": 88.5,
			"zone_name_en": "Dubai Marina",
			"building_name_en": "Admin Verified Tower",
			"permit_location": "Dubai",
			"verification_payload": "{\"ok\":true}",
		}

		with patch("crm.api.redtra.trakheesi.verify_listing", return_value=mock_verification) as mocked_verify:
			doc = frappe.get_doc(
				{
					"doctype": "Property",
					"title": "Admin Trakheesi Verify",
					"listing_type": "Buy",
					"property_type": "Apartment",
					"price": 1200000,
					"currency": "AED",
					"agent": self.agent.name,
					"trakheesi_permit_number": "P-ADMIN-001",
					"trakheesi_qr_code": "/files/admin-qr.png",
					"trakheesi_listing_number": "7123139000",
					"license_number": "723355",
				}
			).insert(ignore_permissions=True)

		mocked_verify.assert_called_once()
		self.assertEqual(doc.trakheesi_listing_guid, "listing-guid-admin-001")
		self.assertEqual(doc.address_line1, "Admin Verified Tower")
		self.assertEqual(doc.status, "Under Verification")

	def test_property_insert_requires_qr_outside_import(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Property",
					"title": "QR Required Outside Import",
					"status": "Draft",
					"listing_type": "Buy",
					"property_type": "Apartment",
					"price": 1250000,
					"currency": "AED",
					"agent": self.agent.name,
					"trakheesi_permit_number": "P-NO-QR-001",
					"trakheesi_listing_number": "7123139000",
					"license_number": "723355",
				}
			).insert(ignore_permissions=True)

	def test_property_import_still_verifies_trakheesi(self):
		mock_verification = {
			"listing_guid": "listing-guid-import-001",
			"validation_url": "https://validation.example/import",
			"verified_at": "2026-05-22 17:30:00",
			"property_size": 95.25,
			"zone_name_en": "Jumeirah Village Circle",
			"building_name_en": "Imported Verified Tower",
			"permit_location": "Dubai",
			"verification_payload": "{\"ok\":true}",
		}

		original_in_import = getattr(frappe.flags, "in_import", False)
		frappe.flags.in_import = True
		try:
			with patch("crm.api.redtra.trakheesi.verify_listing", return_value=mock_verification) as mocked_verify:
				doc = frappe.get_doc(
					{
						"doctype": "Property",
						"title": "Import Trakheesi Verify",
						"status": "Draft",
						"listing_type": "Buy",
						"property_type": "Apartment",
						"price": 1300000,
						"currency": "AED",
						"agent": self.agent.name,
						"trakheesi_permit_number": "P-IMPORT-001",
						"trakheesi_listing_number": "7123139000",
						"license_number": "723355",
					}
				).insert(ignore_permissions=True)

			mocked_verify.assert_called_once()
			self.assertEqual(doc.trakheesi_listing_guid, "listing-guid-import-001")
			self.assertEqual(doc.address_line1, "Imported Verified Tower")
			self.assertEqual(doc.status, "Under Verification")
		finally:
			frappe.flags.in_import = original_in_import

	def test_trakheesi_http_creates_integration_request_log(self):
		mock_response = frappe._dict(
			status_code=200,
			text='{"result":[{"listingNumber":"7123139000","licenseNumber":"723355","permitStatusId":6,"listingGuid":"g1","validationUrl":"https://v.example","property":{"propertySize":70}}],"recordCount":1}',
		)
		mock_response.raise_for_status = lambda: None
		mock_response.json = lambda: {
			"result": [
				{
					"listingNumber": "7123139000",
					"licenseNumber": "723355",
					"permitStatusId": 6,
					"listingGuid": "g1",
					"validationUrl": "https://v.example",
					"property": {"propertySize": 70},
				}
			],
			"recordCount": 1,
		}

		with patch("crm.api.redtra.trakheesi.requests.get", return_value=mock_response):
			from crm.api.redtra import trakheesi

			trakheesi.verify_listing(
				listing_number="7123139000",
				license_number="723355",
			)

		log_name = frappe.db.get_value(
			"Integration Request",
			{
				"integration_request_service": "Trakheesi",
				"request_description": "Trakheesi Listing Validation",
			},
			"name",
			order_by="creation desc",
		)
		self.assertTrue(log_name)
		log = frappe.get_doc("Integration Request", log_name)
		self.assertEqual(log.status, "Completed")
		self.assertIn("7123139000", log.url)
		self.assertIn("***", log.request_headers or "")

	def test_nightly_delist_sets_inactive_unfeatures_and_adds_comment_once(self):
		with patch(
			"crm.api.redtra.trakheesi.verify_listing",
			return_value={
				"listing_guid": "listing-guid-delist-001",
				"validation_url": "https://validation.example/delist",
				"verified_at": "2026-05-22 18:00:00",
				"verification_payload": "{\"ok\":true}",
			},
		):
			property_doc = frappe.get_doc(
				{
					"doctype": "Property",
					"title": "Delist Target",
					"listing_type": "Buy",
					"property_type": "Apartment",
					"price": 900000,
					"currency": "AED",
					"agent": self.agent.name,
					"status": "Active",
					"is_sold": 1,
					"is_featured": 1,
					"featured_until": "2030-01-01 00:00:00",
					"trakheesi_listing_number": "7123139000",
					"license_number": "723355",
					"trakheesi_permit_number": "P-DELIST-001",
					"trakheesi_qr_code": "/files/delist-qr.png",
				}
			).insert(ignore_permissions=True)

		mock_delist_payload = {
			"rows": [
				{
					"listingNumber": "7123139000",
					"LicenseNumber": "723355",
					"delistDate": "2026-05-18T00:00:00",
					"statusNameEn": "Listing Sold",
				}
			],
			"record_count": 1,
		}
		with patch("crm.api.redtra.trakheesi.fetch_delisted_listings", return_value=mock_delist_payload):
			first_run = properties.sync_trakheesi_delisted_properties()
			second_run = properties.sync_trakheesi_delisted_properties()

		updated = frappe.get_doc("Property", property_doc.name)
		self.assertEqual(updated.status, "Inactive")
		self.assertEqual(updated.is_featured, 0)
		self.assertIsNone(updated.featured_until)
		self.assertGreaterEqual(first_run["comment_count"], 1)
		self.assertEqual(second_run["comment_count"], 0)

	def test_nightly_delist_skips_properties_that_are_not_sold_rented_or_inactive(self):
		with patch(
			"crm.api.redtra.trakheesi.verify_listing",
			return_value={
				"listing_guid": "listing-guid-delist-skip-001",
				"validation_url": "https://validation.example/delist-skip",
				"verified_at": "2026-05-22 18:10:00",
				"verification_payload": "{\"ok\":true}",
			},
		):
			property_doc = frappe.get_doc(
				{
					"doctype": "Property",
					"title": "Delist Skip Target",
					"listing_type": "Buy",
					"property_type": "Apartment",
					"price": 850000,
					"currency": "AED",
					"agent": self.agent.name,
					"status": "Draft",
					"is_featured": 1,
					"featured_until": "2030-01-01 00:00:00",
					"trakheesi_listing_number": "7999999000",
					"license_number": "723399",
					"trakheesi_permit_number": "P-DELIST-SKIP-001",
					"trakheesi_qr_code": "/files/delist-skip-qr.png",
				}
			).insert(ignore_permissions=True)

		mock_delist_payload = {
			"rows": [
				{
					"listingNumber": "7999999000",
					"LicenseNumber": "723399",
					"delistDate": "2026-05-18T00:00:00",
					"statusNameEn": "Listing Sold",
				}
			],
			"record_count": 1,
		}
		with patch("crm.api.redtra.trakheesi.fetch_delisted_listings", return_value=mock_delist_payload):
			result = properties.sync_trakheesi_delisted_properties()

		updated = frappe.get_doc("Property", property_doc.name)
		self.assertEqual(updated.status, "Under Verification")
		self.assertEqual(updated.is_featured, 1)
		self.assertEqual(result["reconciled_count"], 0)
