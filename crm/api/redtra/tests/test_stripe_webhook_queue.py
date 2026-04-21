import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today
from unittest.mock import patch

from crm.api.redtra import billing


class TestStripeWebhookQueue(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)
		self._event_logs: list[str] = []

		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"Webhook Agency {self.suffix}",
				"status": "Active",
				"billing_email": f"billing-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)

		self.invoice = frappe.get_doc(
			{
				"doctype": "Agency Billing Invoice",
				"agency": self.agency.name,
				"status": "Open",
				"currency": "AED",
				"invoice_date": today(),
				"billing_period_start": today(),
				"billing_period_end": today(),
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Agency Payment Method", filters={"agency": self.agency.name}, pluck="name"):
			if frappe.db.exists("Agency Payment Method", name):
				frappe.delete_doc("Agency Payment Method", name, ignore_permissions=True, force=1)
		for name in self._event_logs:
			if frappe.db.exists("Stripe Webhook Event", name):
				frappe.delete_doc("Stripe Webhook Event", name, ignore_permissions=True, force=1)
		for name in frappe.get_all("Comment", filters={"reference_doctype": "Agency Billing Invoice", "reference_name": self.invoice.name}, pluck="name"):
			if frappe.db.exists("Comment", name):
				frappe.delete_doc("Comment", name, ignore_permissions=True, force=1)
		for name in frappe.get_all("Comment", filters={"reference_doctype": "Agency", "reference_name": self.agency.name}, pluck="name"):
			if frappe.db.exists("Comment", name):
				frappe.delete_doc("Comment", name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agency Billing Invoice", self.invoice.name):
			frappe.delete_doc("Agency Billing Invoice", self.invoice.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agency", self.agency.name):
			frappe.delete_doc("Agency", self.agency.name, ignore_permissions=True, force=1)
		frappe.db.commit()

	def test_process_invoice_paid_event_marks_invoice_paid(self):
		payload = {
			"id": f"evt_{self.suffix}",
			"type": "invoice.payment_succeeded",
			"data": {
				"object": {
					"status": "paid",
					"payment_intent": f"pi_{self.suffix}",
					"metadata": {"crm_invoice": self.invoice.name, "agency": self.agency.name},
				}
			},
		}
		log = frappe.get_doc(
			{
				"doctype": "Stripe Webhook Event",
				"event_id": payload["id"],
				"event_type": payload["type"],
				"status": "Received",
				"payload_json": frappe.as_json(payload),
				"agency": self.agency.name,
				"crm_invoice": self.invoice.name,
			}
		).insert(ignore_permissions=True)
		self._event_logs.append(log.name)

		result = billing.process_stripe_webhook_event(log.name)
		self.assertTrue(result["ok"])

		invoice = frappe.get_doc("Agency Billing Invoice", self.invoice.name)
		self.assertEqual(invoice.status, "Paid")
		self.assertEqual(invoice.stripe_status, "paid")
		self.assertEqual(invoice.stripe_payment_intent_id, f"pi_{self.suffix}")

		event_log = frappe.get_doc("Stripe Webhook Event", log.name)
		self.assertEqual(event_log.status, "Processed")

	def test_process_customer_updated_syncs_default_payment_method(self):
		self.agency.stripe_customer_id = "cus_sync_test"
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		payload = {
			"id": f"evt_unknown_{self.suffix}",
			"type": "customer.updated",
			"data": {
				"object": {
					"id": "cus_sync_test",
					"metadata": {"agency": self.agency.name},
					"invoice_settings": {"default_payment_method": "pm_sync_default"},
				}
			},
		}
		log = frappe.get_doc(
			{
				"doctype": "Stripe Webhook Event",
				"event_id": payload["id"],
				"event_type": payload["type"],
				"status": "Received",
				"payload_json": frappe.as_json(payload),
				"agency": self.agency.name,
			}
		).insert(ignore_permissions=True)
		self._event_logs.append(log.name)

		class _StripeStub:
			class PaymentMethod:
				@staticmethod
				def retrieve(payment_method_id):
					return {
						"id": payment_method_id,
						"type": "card",
						"card": {
							"brand": "visa",
							"last4": "4242",
							"exp_month": 12,
							"exp_year": 2030,
						},
					}

		with patch("crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), None)):
			result = billing.process_stripe_webhook_event(log.name)
		self.assertTrue(result["ok"])

		event_log = frappe.get_doc("Stripe Webhook Event", log.name)
		self.assertEqual(event_log.status, "Processed")
		self.agency.reload()
		self.assertEqual(self.agency.stripe_default_payment_method_id, "pm_sync_default")
		pm_exists = frappe.db.exists(
			"Agency Payment Method",
			{"agency": self.agency.name, "stripe_payment_method_id": "pm_sync_default"},
		)
		self.assertTrue(pm_exists)

	def test_checkout_completed_creates_payment_method(self):
		self.agency.stripe_customer_id = "cus_checkout_test"
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		payload = {
			"id": f"evt_checkout_{self.suffix}",
			"type": "checkout.session.completed",
			"data": {
				"object": {
					"id": f"cs_{self.suffix}",
					"customer": "cus_checkout_test",
					"setup_intent": "seti_test",
					"metadata": {"agency": self.agency.name, "intent": "billing_setup"},
				}
			},
		}
		log = frappe.get_doc(
			{
				"doctype": "Stripe Webhook Event",
				"event_id": payload["id"],
				"event_type": payload["type"],
				"status": "Received",
				"payload_json": frappe.as_json(payload),
				"agency": self.agency.name,
			}
		).insert(ignore_permissions=True)
		self._event_logs.append(log.name)

		class _StripeStub:
			class SetupIntent:
				@staticmethod
				def retrieve(setup_intent_id, expand=None):
					return {
						"id": setup_intent_id,
						"payment_method": {
							"id": "pm_checkout_default",
							"type": "card",
							"card": {
								"brand": "visa",
								"last4": "1111",
								"exp_month": 10,
								"exp_year": 2032,
							},
						},
					}

			class Customer:
				@staticmethod
				def modify(customer_id, invoice_settings=None):
					return {"id": customer_id, "invoice_settings": invoice_settings}

		with patch("crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), None)):
			result = billing.process_stripe_webhook_event(log.name)
		self.assertTrue(result["ok"])

		event_log = frappe.get_doc("Stripe Webhook Event", log.name)
		self.assertEqual(event_log.status, "Processed")
		self.agency.reload()
		self.assertEqual(self.agency.stripe_default_payment_method_id, "pm_checkout_default")
