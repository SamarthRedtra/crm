import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from crm.api.redtra.fcm import send_push_to_user


class TestFCMPush(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		settings = frappe.get_single("FCRM Settings")
		settings.mobile_push_provider = "Darify Firebase"
		settings.firebase_project_id = "darify-b9ff8"
		service_account = {
			"type": "service_account",
			"project_id": "darify-b9ff8",
			"private_key_id": "test",
			"private_key": "-----BEGIN PRIVATE KEY-----\nMIIBVwIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAkEAp-test\n-----END PRIVATE KEY-----\n",
			"client_email": "firebase-adminsdk@test.iam.gserviceaccount.com",
			"client_id": "123",
			"auth_uri": "https://accounts.google.com/o/oauth2/auth",
			"token_uri": "https://oauth2.googleapis.com/token",
		}
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "firebase-service-account-test.json",
				"content": json.dumps(service_account),
				"is_private": 1,
			}
		)
		file_doc.save(ignore_permissions=True)
		settings.firebase_service_account_key = file_doc.file_url
		settings.save(ignore_permissions=True)

	def test_send_push_to_user_without_tokens(self):
		result = send_push_to_user("nobody@example.com", "Hello", "World")
		self.assertFalse(result["ok"])
		self.assertEqual(result["token_count"], 0)
		self.assertEqual(result["provider"], "Darify Firebase")

	@patch("crm.api.redtra.fcm._get_access_token", return_value="test-token")
	@patch("crm.api.redtra.fcm.requests.post")
	def test_send_push_to_user_success(self, mock_post, _mock_token):
		mock_post.return_value.ok = True
		mock_post.return_value.status_code = 200
		mock_post.return_value.json.return_value = {"name": "projects/darify-b9ff8/messages/0"}

		frappe.get_doc(
			{
				"doctype": "Raven Push Token",
				"user": "test_push@example.com",
				"environment": "Mobile",
				"fcm_token": "test-fcm-token",
			}
		).insert(ignore_permissions=True)

		result = send_push_to_user("test_push@example.com", "Hello", "World", {"type": "test"})
		self.assertTrue(result["ok"])
		self.assertEqual(result["sent_count"], 1)
		self.assertEqual(result["provider"], "Darify Firebase")

		payload = mock_post.call_args.kwargs["json"]
		self.assertEqual(payload["message"]["token"], "test-fcm-token")
		self.assertEqual(payload["message"]["notification"]["title"], "Hello")
