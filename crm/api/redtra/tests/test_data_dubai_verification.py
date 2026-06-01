import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from crm.api.redtra import agencies, auth, billing, data_dubai, onboarding, utils


class MockRequest:
	def __init__(self, data=None, headers=None, method="GET"):
		self.json = data or {}
		self.method = method
		self.headers = headers or {}

	def get_json(self):
		return self.json


class TestDataDubaiVerification(IntegrationTestCase):
	def setUp(self):
		self.search_patcher = patch("frappe.model.document.update_global_search")
		self.search_patcher.start()
		frappe.set_user("Administrator")
		frappe.reload_doc("fcrm", "doctype", "fcrm_settings", force=True)
		frappe.reload_doc("fcrm", "doctype", "agency", force=True)
		frappe.reload_doc("fcrm", "doctype", "agent", force=True)

		self.suffix = frappe.generate_hash(length=6)
		settings = frappe.get_single("FCRM Settings")
		settings.dda_base_url = ""
		settings.dda_security_identifier = ""
		settings.dda_client_id = ""
		settings.dda_client_secret = ""
		settings.dda_entity = ""
		settings.dda_broker_dataset_name = ""
		settings.dda_real_estate_dataset_name = ""
		settings.dda_request_timeout_seconds = 10
		settings.save(ignore_permissions=True)

		self.user_email = f"dda-agent-{self.suffix}@example.com"
		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": self.user_email,
				"first_name": "DDA",
				"last_name": "Agent",
				"send_welcome_email": 0,
				"enabled": 1,
				"roles": [{"role": "Agent"}],
			}
		).insert(ignore_permissions=True)

		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"DDA Agency {self.suffix}",
				"status": "Active",
				"email": f"agency-{self.suffix}@example.com",
				"phone": "+971500000001",
				"whatsapp_number": "+971500000001",
				"brn_id": f"AG-BRN-{self.suffix}",
				"rera_id": f"AG-RERA-{self.suffix}",
				"company_license_number": f"LIC-{self.suffix}",
				"billing_contact_name": "Admin",
				"billing_email": f"billing-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)

		self.agent = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": self.user.name,
				"agency": self.agency.name,
				"agency_role": "Admin",
				"status": "Verified",
				"phone": "+971500000002",
				"whatsapp_number": "+971500000002",
				"dfd_registration_id": f"DFD-{self.suffix}",
				"brn_id": f"BRN-{self.suffix}",
			}
		).insert(ignore_permissions=True)

		settings = frappe.get_single("FCRM Settings")
		settings.dda_base_url = "https://example.data.dubai"
		settings.dda_security_identifier = "security-id"
		settings.dda_client_id = "client-id"
		settings.dda_client_secret = "client-secret"
		settings.dda_entity = "dld"
		settings.dda_broker_dataset_name = "dld_brokers-open-api"
		settings.dda_real_estate_dataset_name = "dld_real_estate_licenses-open-api"
		settings.dda_request_timeout_seconds = 10
		settings.save(ignore_permissions=True)

	def tearDown(self):
		self.search_patcher.stop()
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_data_dubai_verification_creates_integration_request_log(self):
		token_response = frappe._dict(status_code=200)
		token_response.raise_for_status = lambda: None
		token_response.json = lambda: {
			"access_token": "token-123",
			"expires_in": 3600,
			"token_type": "Bearer",
		}

		dataset_response = frappe._dict(status_code=200)
		dataset_response.raise_for_status = lambda: None
		dataset_response.json = lambda: {
			"results": [
				{
					"company_license_number": f"LIC-{self.suffix}",
					"agency_name": "Verified DDA Agency",
					"license_expiry_date": "2030-01-01",
				}
			]
		}

		with patch("crm.api.redtra.data_dubai.requests.post", return_value=token_response), patch(
			"crm.api.redtra.data_dubai.requests.get", return_value=dataset_response
		):
			verification = data_dubai.verify_real_estate_license(
				agency_name="Verified DDA Agency",
				company_license_number=self.agency.company_license_number,
				reference_doctype="Agency",
				reference_docname=self.agency.name,
			)

		self.assertEqual(verification["status"], data_dubai.STATUS_VERIFIED)
		log_name = frappe.db.get_value(
			"Integration Request",
			{
				"integration_request_service": "Data Dubai",
				"request_description": "DDA Real Estate License Verification",
			},
			"name",
			order_by="creation desc",
		)
		self.assertTrue(log_name)
		log = frappe.get_doc("Integration Request", log_name)
		self.assertEqual(log.status, "Completed")
		self.assertIn("***", log.request_headers or "")

	def test_registration_normalizes_agency_name_and_persists_expiry(self):
		frappe.set_user("Guest")
		payload = {
			"full_name": "Agency Admin",
			"email": f"onboard-{self.suffix}@example.com",
			"password": "TestPass123!",
			"agency_name": f"Wrong Agency Name {self.suffix}",
			"brn_id": f"ONB-BRN-{self.suffix}",
			"rera_id": f"ONB-RERA-{self.suffix}",
			"company_license_number": f"ONB-LIC-{self.suffix}",
			"phone": "+971500000099",
			"agency_phone": "+971500000099",
			"challenge_id": "test",
			"challenge_answer": "test",
		}
		with patch("crm.api.redtra.onboarding._validate_challenge", return_value=None), patch(
			"crm.api.redtra.data_dubai.is_configured", return_value=True
		), patch(
			"crm.api.redtra.data_dubai.verify_real_estate_license",
			return_value={
				"status": data_dubai.STATUS_VERIFIED,
				"verified": True,
				"expiry_date": "2031-05-01",
				"verified_agency_name": f"Verified Agency {self.suffix}",
				"agency_match_status": data_dubai.AGENCY_MATCH_MISMATCH,
				"checked_on": "2026-05-27 07:00:00",
				"notes": "Verified from DDA",
				"payload": "{\"ok\":true}",
			},
		):
			result = onboarding.register_agency_admin(data=payload)

		agency = frappe.get_doc("Agency", result["agency"])
		self.assertEqual(agency.agency_name, f"Verified Agency {self.suffix}")
		self.assertEqual(agency.dda_real_estate_license_status, data_dubai.STATUS_VERIFIED)
		self.assertEqual(str(agency.dda_real_estate_license_expiry_date), "2031-05-01")

	def test_agent_onboarding_blocks_when_broker_does_not_match_agency(self):
		self.agent.status = "Pending Verification"
		with patch("crm.api.redtra.data_dubai.is_configured", return_value=True), patch(
			"crm.api.redtra.data_dubai.verify_broker_license",
			return_value={
				"status": data_dubai.STATUS_MISMATCH,
				"verified": False,
				"expiry_date": "2030-12-31",
				"verified_agency_name": "Another Agency",
				"agency_match_status": data_dubai.AGENCY_MATCH_MISMATCH,
				"checked_on": "2026-05-27 07:10:00",
				"notes": "The broker does not belong to the selected agency in Data Dubai.",
				"payload": "{\"ok\":false}",
			},
		):
			with self.assertRaises(frappe.ValidationError):
				self.agent.save(ignore_permissions=True)

	def test_billing_context_exposes_license_verification_flags(self):
		self.agency.dda_real_estate_license_status = data_dubai.STATUS_EXPIRED
		self.agency.dda_real_estate_license_expiry_date = "2025-01-01"
		frappe.db.set_value(
			"Agency",
			self.agency.name,
			{
				"dda_real_estate_license_status": data_dubai.STATUS_EXPIRED,
				"dda_real_estate_license_expiry_date": "2025-01-01",
			},
			update_modified=False,
		)

		frappe.db.set_value(
			"Agent",
			self.agent.name,
			{
				"dda_broker_license_status": data_dubai.STATUS_MISMATCH,
				"dda_broker_license_expiry_date": "2030-01-01",
				"dda_agency_match_status": data_dubai.AGENCY_MATCH_MISMATCH,
			},
			update_modified=False,
		)

		frappe.set_user(self.user.name)
		context = billing.get_session_agency_context()

		self.assertTrue(context["requires_license_verification"])
		self.assertTrue(context["requires_agency_license_verification"])
		self.assertTrue(context["requires_agent_license_verification"])
		self.assertEqual(context["agency_license_status"], data_dubai.STATUS_EXPIRED)
		self.assertEqual(context["agent_license_status"], data_dubai.STATUS_MISMATCH)

	def test_agent_and_agency_payloads_include_license_fields(self):
		frappe.db.set_value(
			"Agency",
			self.agency.name,
			{
				"dda_real_estate_license_status": data_dubai.STATUS_VERIFIED,
				"dda_real_estate_license_expiry_date": "2032-01-01",
				"dda_verified_agency_name": self.agency.agency_name,
				"dda_verification_checked_on": "2026-05-27 07:15:00",
			},
			update_modified=False,
		)

		frappe.db.set_value(
			"Agent",
			self.agent.name,
			{
				"dda_broker_license_status": data_dubai.STATUS_VERIFIED,
				"dda_broker_license_expiry_date": "2031-01-01",
				"dda_agency_match_status": data_dubai.AGENCY_MATCH_MATCHED,
				"dda_verified_agency_name": self.agency.agency_name,
				"dda_verification_checked_on": "2026-05-27 07:15:00",
			},
			update_modified=False,
		)

		headers = {"Authorization": f"Bearer {utils.generate_jwt(self.user.name)}"}
		frappe.set_user(self.user.name)
		frappe.local.request = MockRequest(headers=headers)
		with patch("crm.api.redtra.utils.extract_bearer_token", return_value="fake"), patch(
			"crm.api.redtra.utils.decode_jwt", return_value={"user": self.user.name}
		):
			profile = auth.get_profile()
		self.assertEqual(profile["agent_profile"]["broker_license_status"], data_dubai.STATUS_VERIFIED)
		self.assertEqual(str(profile["agent_profile"]["broker_license_expiry_date"]), "2031-01-01")
		self.assertEqual(profile["agency"]["real_estate_license_status"], data_dubai.STATUS_VERIFIED)
		self.assertEqual(str(profile["agency"]["real_estate_license_expiry_date"]), "2032-01-01")

		frappe.set_user("Guest")
		agent_payload = agencies.list_agency_agents(self.agency.name)
		self.assertEqual(agent_payload["items"][0]["broker_license_status"], data_dubai.STATUS_VERIFIED)

		agency_payload = agencies.get_agency(self.agency.name)
		self.assertEqual(agency_payload["real_estate_license_status"], data_dubai.STATUS_VERIFIED)
