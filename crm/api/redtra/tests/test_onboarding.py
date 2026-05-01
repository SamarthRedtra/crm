import re

import frappe
from frappe.tests import IntegrationTestCase

from crm.api.redtra import onboarding


class TestAgencyOnboardingRegistration(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)

	def tearDown(self):
		frappe.set_user("Administrator")
		email = getattr(self, "_cleanup_email", None)
		agency_id = getattr(self, "_cleanup_agency", None)
		if email:
			agent = frappe.db.get_value("Agent", {"user": email}, "name")
			if agent and frappe.db.exists("Agent", agent):
				frappe.delete_doc("Agent", agent, ignore_permissions=True, force=1)
		if agency_id and frappe.db.exists("Agency", agency_id):
			frappe.delete_doc("Agency", agency_id, ignore_permissions=True, force=1)
		if email and frappe.db.exists("User", email):
			frappe.delete_doc("User", email, ignore_permissions=True, force=1)
		frappe.db.commit()

	def _parse_sum_from_prompt(self, prompt: str) -> str:
		match = re.search(r"What is (\d+) \+ (\d+)", prompt or "")
		self.assertIsNotNone(match, msg=f"Unexpected prompt format: {prompt!r}")
		a, b = int(match.group(1)), int(match.group(2))
		return str(a + b)

	def test_registration_challenge_and_signup(self):
		frappe.set_user("Guest")
		ch = onboarding.get_registration_challenge()
		self.assertIn("challenge_id", ch)
		self.assertIn("prompt", ch)
		answer = self._parse_sum_from_prompt(ch["prompt"])

		email = f"onboarding-{self.suffix}@example.com"
		payload = {
			"full_name": "Test Admin",
			"email": email,
			"password": "TestPass123!",
			"agency_name": f"Onboarding Agency {self.suffix}",
			"brn_id": f"BRN-{self.suffix}",
			"rera_id": f"RERA-{self.suffix}",
			"challenge_id": ch["challenge_id"],
			"challenge_answer": answer,
			"idempotency_key": f"idem-{self.suffix}",
		}
		result = onboarding.register_agency_admin(data=payload)
		self.assertTrue(result.get("ok"))
		self.assertEqual(result.get("user"), email)
		self._cleanup_email = email
		self._cleanup_agency = result.get("agency")

		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("User", email))
		agency_name = result.get("agency")
		self.assertTrue(agency_name and frappe.db.exists("Agency", agency_name))
		agency = frappe.get_doc("Agency", agency_name)
		self.assertEqual(getattr(agency, "verification_status", None), "Pending Verification")

		# Idempotent replay returns cached payload
		frappe.set_user("Guest")
		result2 = onboarding.register_agency_admin(data=payload)
		self.assertEqual(result2.get("user"), email)

	def test_registration_requires_valid_challenge(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			onboarding.register_agency_admin(
				data={
					"full_name": "X",
					"email": f"bad-{self.suffix}@example.com",
					"password": "TestPass123!",
					"agency_name": f"Bad Agency {self.suffix}",
					"challenge_id": "invalid",
					"challenge_answer": "99",
				}
			)

	def test_registration_requires_brn_and_rera(self):
		frappe.set_user("Guest")
		ch = onboarding.get_registration_challenge()
		answer = self._parse_sum_from_prompt(ch["prompt"])
		with self.assertRaises(frappe.ValidationError):
			onboarding.register_agency_admin(
				data={
					"full_name": "Test Admin",
					"email": f"missing-ids-{self.suffix}@example.com",
					"password": "TestPass123!",
					"agency_name": f"Missing IDs Agency {self.suffix}",
					"challenge_id": ch["challenge_id"],
					"challenge_answer": answer,
				}
			)
