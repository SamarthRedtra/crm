import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, cint, now_datetime, today
from unittest.mock import patch

from crm.api.redtra import billing, permissions, properties as properties_api


class TestAgencyBilling(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.reload_doc("fcrm", "doctype", "property", force=True)
		frappe.reload_doc("fcrm", "doctype", "property_featured_log", force=True)
		self.suffix = frappe.generate_hash(length=8)
		self._created_invoices: set[str] = set()

		settings = frappe.get_single("Agency Billing Settings")
		settings.default_currency = "AED"
		settings.invoice_due_days = 7
		settings.billing_enabled = 1
		settings.addon_charge_timing = "daily_accrual"
		settings.flags.ignore_permissions = True
		settings.save()

		self.user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"agency-admin-{self.suffix}@example.com",
				"first_name": "Agency",
				"last_name": "Admin",
				"send_welcome_email": 0,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		if frappe.db.exists("Role", "Agent"):
			self.user.add_roles("Agent")

		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"Billing Agency {self.suffix}",
				"status": "Active",
				"email": f"agency-{self.suffix}@example.com",
				"phone": "+971500000001",
				"whatsapp_number": "+971500000001",
				"billing_contact_name": "Billing Admin",
				"billing_email": f"billing-{self.suffix}@example.com",
			}
		).insert(ignore_permissions=True)

		self._level_created = False
		_existing_level = frappe.get_all("Agent Level", pluck="name", order_by="sort_order asc, level_name asc", limit=1)
		if _existing_level:
			self.level = frappe.get_doc("Agent Level", _existing_level[0])
		else:
			self.level = frappe.get_doc(
				{
					"doctype": "Agent Level",
					"level_name": f"Gold {self.suffix}",
					"daily_rate": 150,
					"currency": "AED",
					"active": 1,
				}
			).insert(ignore_permissions=True)
			self._level_created = True

		self.addon = frappe.get_doc(
			{
				"doctype": "Billing Addon",
				"addon_name": f"Featured Listings {self.suffix}",
				"pricing_model": "Daily Fixed",
				"rate": 25,
				"currency": "AED",
				"active": 1,
			}
		).insert(ignore_permissions=True)

		self._featured_addon_created = False
		featured_addon_name = frappe.db.get_value(
			"Billing Addon",
			{"addon_name": billing.FEATURED_ADDON_NAME},
			"name",
		)
		if featured_addon_name:
			self.featured_addon = frappe.get_doc("Billing Addon", featured_addon_name)
		else:
			self.featured_addon = frappe.get_doc(
				{
					"doctype": "Billing Addon",
					"addon_name": billing.FEATURED_ADDON_NAME,
					"pricing_model": "Daily Fixed",
					"rate": 600,
					"currency": "AED",
					"active": 1,
					"requires_upfront_payment": 1,
				}
			).insert(ignore_permissions=True)
			self._featured_addon_created = True

		self.agency.append(
			"billing_addons",
			{
				"addon": self.addon.name,
				"quantity": 1,
				"enabled": 1,
			},
		)
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		self.agent = frappe.get_doc(
			{
				"doctype": "Agent",
				"user": self.user.name,
				"phone": "+971500000003",
				"whatsapp_number": "+971500000003",
				"status": "Verified",
				"dfd_registration_id": f"DFD-{self.suffix}",
				"agency": self.agency.name,
				"agency_role": "Admin",
				"agent_level": self.level.name,
				"billable": 1,
			}
		).insert(ignore_permissions=True)

		self.featured_properties = []
		for idx in range(2):
			doc = frappe.get_doc(
				{
					"doctype": "Property",
					"title": f"Featured Property {idx + 1} {self.suffix}",
					"listing_type": "Buy",
					"property_type": "Apartment",
					"price": 1000000 + (idx * 100000),
					"currency": "AED",
					"agent": self.agent.name,
					"agency": self.agency.name,
					"status": "Active",
					"completion_status": "Ready",
				}
			).insert(ignore_permissions=True)
			self.featured_properties.append(doc.name)

		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for payment_method_name in frappe.get_all("Agency Payment Method", filters={"agency": self.agency.name}, pluck="name"):
			if frappe.db.exists("Agency Payment Method", payment_method_name):
				frappe.delete_doc("Agency Payment Method", payment_method_name, ignore_permissions=True, force=1)
		for invoice_name in frappe.get_all("Agency Billing Invoice", filters={"agency": self.agency.name}, pluck="name"):
			if frappe.db.exists("Agency Billing Invoice", invoice_name):
				frappe.delete_doc("Agency Billing Invoice", invoice_name, ignore_permissions=True, force=1)
		for accrual_name in frappe.get_all("Agency Billing Accrual", filters={"agency": self.agency.name}, pluck="name"):
			if frappe.db.exists("Agency Billing Accrual", accrual_name):
				frappe.delete_doc("Agency Billing Accrual", accrual_name, ignore_permissions=True, force=1)
		for property_name in getattr(self, "featured_properties", []):
			for log_name in frappe.get_all(
				"Property Featured Log",
				filters={"property": property_name},
				pluck="name",
			):
				if frappe.db.exists("Property Featured Log", log_name):
					frappe.delete_doc("Property Featured Log", log_name, ignore_permissions=True, force=1)
			if frappe.db.exists("Property", property_name):
				frappe.delete_doc("Property", property_name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agent", self.agent.name):
			frappe.delete_doc("Agent", self.agent.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Agency", self.agency.name):
			frappe.delete_doc("Agency", self.agency.name, ignore_permissions=True, force=1)
		if frappe.db.exists("Billing Addon", self.addon.name):
			frappe.delete_doc("Billing Addon", self.addon.name, ignore_permissions=True, force=1)
		if (
			getattr(self, "_featured_addon_created", False)
			and getattr(self, "featured_addon", None)
			and frappe.db.exists("Billing Addon", self.featured_addon.name)
		):
			frappe.delete_doc("Billing Addon", self.featured_addon.name, ignore_permissions=True, force=1)
		if getattr(self, "_level_created", False) and frappe.db.exists("Agent Level", self.level.name):
			frappe.delete_doc("Agent Level", self.level.name, ignore_permissions=True, force=1)
		if frappe.db.exists("User", self.user.name):
			frappe.delete_doc("User", self.user.name, ignore_permissions=True, force=1)
		frappe.db.commit()

	def test_daily_billing_creates_level_and_addon_accruals(self):
		billing.run_daily_agency_billing("2026-02-28")

		accruals = frappe.get_all(
			"Agency Billing Accrual",
			filters={"agency": self.agency.name, "posting_date": "2026-02-28"},
			fields=["entry_type", "amount", "currency"],
			order_by="entry_type asc",
		)
		self.assertEqual(len(accruals), 2)
		self.assertEqual(accruals[0]["currency"], "AED")
		self.assertEqual(sum(row["amount"] for row in accruals), 175)

	def test_monthly_close_creates_invoice_and_marks_accruals(self):
		billing.run_daily_agency_billing("2026-02-28")

		invoices = billing._close_billing_period(
			period_start="2026-02-01",
			period_end="2026-02-28",
			agency_id=self.agency.name,
			sync_to_stripe=False,
		)

		self.assertEqual(len(invoices), 1)
		invoice = frappe.get_doc("Agency Billing Invoice", invoices[0]["name"])
		self.assertEqual(invoice.total, 175)
		self.assertEqual(invoice.status, "Draft")

		accrual_statuses = frappe.get_all(
			"Agency Billing Accrual",
			filters={"agency": self.agency.name, "invoice": invoice.name},
			pluck="status",
		)
		self.assertTrue(accrual_statuses)
		self.assertTrue(all(status == "Invoiced" for status in accrual_statuses))

	def test_agency_admin_context_grants_billing_access(self):
		frappe.set_user(self.user.name)

		context = billing.get_session_agency_context()

		self.assertEqual(context["agency"], self.agency.name)
		self.assertTrue(context["can_manage_billing"])
		self.assertTrue(context["can_manage_team"])
		self.assertTrue(permissions.has_agency_permission(self.agency, self.user.name, "write"))
		self.assertTrue(
			permissions.has_agency_billing_permission(
				frappe.get_doc(
					{
						"doctype": "Agency Billing Invoice",
						"agency": self.agency.name,
						"status": "Draft",
						"currency": "AED",
						"invoice_date": "2026-02-28",
						"billing_period_start": "2026-02-01",
						"billing_period_end": "2026-02-28",
					}
				),
				self.user.name,
				"read",
			)
		)

	def test_billing_disabled_skips_background_generation(self):
		settings = frappe.get_single("Agency Billing Settings")
		settings.billing_enabled = 0
		settings.flags.ignore_permissions = True
		settings.save()

		daily_result = billing.run_daily_agency_billing("2026-02-28")
		self.assertEqual(daily_result.get("created"), 0)
		self.assertEqual(daily_result.get("skipped"), "billing_disabled")

		invoices = billing._close_billing_period(
			period_start="2026-02-01",
			period_end="2026-02-28",
			agency_id=self.agency.name,
			sync_to_stripe=False,
		)
		self.assertEqual(invoices, [])

	def test_record_usage_requires_positive_quantity(self):
		with self.assertRaises(frappe.ValidationError):
			billing.record_addon_usage(
				agency_id=self.agency.name,
				addon=self.addon.name,
				quantity=0,
			)

	def test_upfront_addon_charge_creates_immediate_stripe_invoice(self):
		settings = frappe.get_single("Agency Billing Settings")
		settings.addon_charge_timing = "upfront_immediate"
		settings.flags.ignore_permissions = True
		settings.save()
		self.agency.stripe_customer_id = "cus_upfront_ok"
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		class _StripeStub:
			class Invoice:
				@staticmethod
				def list(customer=None, limit=20):
					return frappe._dict(data=[])

				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="in_upfront_ok", status="draft", hosted_invoice_url="https://stripe.test/in_upfront_ok")

				@staticmethod
				def finalize_invoice(invoice_id):
					return frappe._dict(id=invoice_id, status="open", hosted_invoice_url="https://stripe.test/in_upfront_ok")

			class InvoiceItem:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="ii_upfront_ok")

			class Customer:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="cus_upfront_ok")

		with patch("crm.api.redtra.billing._stripe_enabled", return_value=True), patch(
			"crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), settings)
		):
			out = billing.update_current_agency_profile(
				agency_id=self.agency.name,
				data=frappe.as_json(
					{
						"billing_addons": [
							{
								"addon": self.addon.name,
								"quantity": 2,
								"enabled": 1,
							}
						]
					}
				),
			)

		upfront = out.get("upfront_addon_charges") or {}
		self.assertEqual(upfront.get("attempted"), 1)
		self.assertEqual(upfront.get("charged"), 1)
		self.assertEqual(upfront.get("failed"), 0)
		invoices = frappe.get_all(
			"Agency Billing Invoice",
			filters={"agency": self.agency.name, "billing_period_start": today(), "billing_period_end": today()},
			fields=["name", "status", "stripe_invoice_id"],
		)
		self.assertEqual(len(invoices), 1)
		self.assertEqual(invoices[0]["status"], "Open")
		self.assertEqual(invoices[0]["stripe_invoice_id"], "in_upfront_ok")

	def test_upfront_addon_charge_is_idempotent_for_same_state(self):
		settings = frappe.get_single("Agency Billing Settings")
		settings.addon_charge_timing = "upfront_immediate"
		settings.flags.ignore_permissions = True
		settings.save()
		self.agency.stripe_customer_id = "cus_upfront_idempotent"
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		class _StripeStub:
			class Invoice:
				@staticmethod
				def list(customer=None, limit=20):
					return frappe._dict(data=[])

				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="in_upfront_idempotent", status="draft", hosted_invoice_url="https://stripe.test/in_upfront_idempotent")

				@staticmethod
				def finalize_invoice(invoice_id):
					return frappe._dict(id=invoice_id, status="open", hosted_invoice_url="https://stripe.test/in_upfront_idempotent")

			class InvoiceItem:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="ii_upfront_idempotent")

			class Customer:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="cus_upfront_idempotent")

		payload = frappe.as_json({"billing_addons": [{"addon": self.addon.name, "quantity": 2, "enabled": 1}]})
		with patch("crm.api.redtra.billing._stripe_enabled", return_value=True), patch(
			"crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), settings)
		):
			first = billing.update_current_agency_profile(agency_id=self.agency.name, data=payload)
			second = billing.update_current_agency_profile(agency_id=self.agency.name, data=payload)

		self.assertEqual((first.get("upfront_addon_charges") or {}).get("charged"), 1)
		self.assertEqual((second.get("upfront_addon_charges") or {}).get("charged"), 0)
		self.assertEqual(
			frappe.db.count("Agency Billing Invoice", {"agency": self.agency.name, "billing_period_start": today()}),
			1,
		)

	def test_upfront_addon_charge_failure_marks_invoice_failed(self):
		settings = frappe.get_single("Agency Billing Settings")
		settings.addon_charge_timing = "upfront_immediate"
		settings.flags.ignore_permissions = True
		settings.save()
		self.agency.stripe_customer_id = "cus_upfront_failed"
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		class _StripeStub:
			class Invoice:
				@staticmethod
				def list(customer=None, limit=20):
					return frappe._dict(data=[])

				@staticmethod
				def create(**kwargs):
					raise RuntimeError("stripe unavailable")

			class InvoiceItem:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="ii_failed")

			class Customer:
				@staticmethod
				def create(**kwargs):
					return frappe._dict(id="cus_upfront_failed")

		with patch("crm.api.redtra.billing._stripe_enabled", return_value=True), patch(
			"crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), settings)
		):
			out = billing.update_current_agency_profile(
				agency_id=self.agency.name,
				data=frappe.as_json({"billing_addons": [{"addon": self.addon.name, "quantity": 3, "enabled": 1}]}),
			)

		upfront = out.get("upfront_addon_charges") or {}
		self.assertEqual(upfront.get("attempted"), 1)
		self.assertEqual(upfront.get("failed"), 1)
		invoice_name = (upfront.get("invoices") or [])[0]["name"]
		invoice = frappe.get_doc("Agency Billing Invoice", invoice_name)
		self.assertEqual(invoice.status, "Failed")
		self.assertTrue(invoice.error_message)

	def test_daily_billing_skips_fixed_addons_in_upfront_mode(self):
		settings = frappe.get_single("Agency Billing Settings")
		settings.addon_charge_timing = "upfront_immediate"
		settings.flags.ignore_permissions = True
		settings.save()

		billing.run_daily_agency_billing("2026-02-28")
		accruals = frappe.get_all(
			"Agency Billing Accrual",
			filters={"agency": self.agency.name, "posting_date": "2026-02-28"},
			fields=["entry_type", "addon", "amount"],
		)
		addon_rows = [row for row in accruals if row["entry_type"] == "Addon"]
		self.assertFalse(addon_rows)

	def test_redirect_url_validation_rejects_external_hosts(self):
		with self.assertRaises(frappe.ValidationError):
			billing._validate_redirect_url("https://example.com/bad", "https://good.test")

	def test_has_billing_setup_requires_default_payment_method(self):
		self.agency.stripe_customer_id = "cus_test_only"
		self.agency.stripe_default_payment_method_id = None
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		self.assertFalse(billing._has_billing_setup(self.agency))

		self.agency.stripe_default_payment_method_id = "pm_default"
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		self.assertTrue(billing._has_billing_setup(self.agency))

	def test_list_saved_payment_methods_excludes_detached(self):
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_active",
				"status": "Active",
				"is_default": 1,
				"type": "card",
				"brand": "visa",
				"last4": "4242",
				"exp_month": 12,
				"exp_year": 2030,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_detached",
				"status": "Detached",
				"is_default": 0,
				"type": "card",
				"brand": "mastercard",
				"last4": "4444",
				"exp_month": 11,
				"exp_year": 2031,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.user.name)
		result = billing.list_saved_payment_methods(agency_id=self.agency.name)
		self.assertEqual(len(result["saved_payment_methods"]), 1)
		self.assertEqual(result["saved_payment_methods"][0]["stripe_payment_method_id"], "pm_active")

	def test_set_default_payment_method_updates_local_state(self):
		self.agency.stripe_customer_id = "cus_saved"
		self.agency.stripe_default_payment_method_id = "pm_old"
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_old",
				"status": "Active",
				"is_default": 1,
				"type": "card",
				"brand": "visa",
				"last4": "4242",
				"exp_month": 12,
				"exp_year": 2030,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_new",
				"status": "Active",
				"is_default": 0,
				"type": "card",
				"brand": "mastercard",
				"last4": "4444",
				"exp_month": 11,
				"exp_year": 2031,
			}
		).insert(ignore_permissions=True)

		class _StripeStub:
			class Customer:
				@staticmethod
				def modify(customer_id, invoice_settings=None):
					return {"id": customer_id, "invoice_settings": invoice_settings}

		with patch("crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), None)):
			result = billing.set_default_payment_method(
				agency_id=self.agency.name,
				stripe_payment_method_id="pm_new",
			)
		self.assertEqual(result["default_payment_method_id"], "pm_new")
		self.agency.reload()
		self.assertEqual(self.agency.stripe_default_payment_method_id, "pm_new")
		old_default = frappe.db.get_value(
			"Agency Payment Method",
			{"agency": self.agency.name, "stripe_payment_method_id": "pm_old"},
			"is_default",
		)
		new_default = frappe.db.get_value(
			"Agency Payment Method",
			{"agency": self.agency.name, "stripe_payment_method_id": "pm_new"},
			"is_default",
		)
		self.assertEqual(cint(old_default), 0)
		self.assertEqual(cint(new_default), 1)

	def test_detach_payment_method_reassigns_default(self):
		self.agency.stripe_customer_id = "cus_saved"
		self.agency.stripe_default_payment_method_id = "pm_default"
		self.agency.flags.ignore_permissions = True
		self.agency.save()
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_default",
				"status": "Active",
				"is_default": 1,
				"type": "card",
				"brand": "visa",
				"last4": "4242",
				"exp_month": 12,
				"exp_year": 2030,
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Agency Payment Method",
				"agency": self.agency.name,
				"stripe_customer_id": "cus_saved",
				"stripe_payment_method_id": "pm_backup",
				"status": "Active",
				"is_default": 0,
				"type": "card",
				"brand": "mastercard",
				"last4": "4444",
				"exp_month": 11,
				"exp_year": 2031,
			}
		).insert(ignore_permissions=True)

		class _StripeStub:
			class PaymentMethod:
				@staticmethod
				def detach(payment_method_id):
					return {"id": payment_method_id}

			class Customer:
				@staticmethod
				def modify(customer_id, invoice_settings=None):
					return {"id": customer_id, "invoice_settings": invoice_settings}

		with patch("crm.api.redtra.billing._get_stripe_sdk", return_value=(_StripeStub(), None)):
			result = billing.detach_payment_method(
				agency_id=self.agency.name,
				stripe_payment_method_id="pm_default",
			)
		self.assertEqual(result["default_payment_method_id"], "pm_backup")
		self.agency.reload()
		self.assertEqual(self.agency.stripe_default_payment_method_id, "pm_backup")
		detached_status = frappe.db.get_value(
			"Agency Payment Method",
			{"agency": self.agency.name, "stripe_payment_method_id": "pm_default"},
			["status", "is_default"],
			as_dict=True,
		)
		self.assertEqual(detached_status.status, "Detached")
		self.assertEqual(cint(detached_status.is_default), 0)

	def test_featured_checkout_completion_is_idempotent(self):
		frappe.set_user(self.user.name)
		self.agency.reload()
		self.agency.stripe_customer_id = "cus_featured_checkout"
		self.agency.flags.ignore_permissions = True
		self.agency.save()

		class _StripeStub:
			class checkout:
				class Session:
					metadata = {}

					@staticmethod
					def create(**kwargs):
						_StripeStub.checkout.Session.metadata = kwargs.get("metadata") or {}
						return frappe._dict(id="cs_featured_checkout", url="https://stripe.test/featured_checkout")

					@staticmethod
					def retrieve(session_id):
						return frappe._dict(
							id=session_id,
							metadata=_StripeStub.checkout.Session.metadata,
							payment_status="paid",
							status="complete",
							payment_intent="pi_featured_checkout",
						)

		with patch("crm.api.redtra.billing._stripe_enabled", return_value=True), patch(
			"crm.api.redtra.billing._get_stripe_sdk",
			return_value=(_StripeStub(), frappe.get_single("Agency Billing Settings")),
		):
			created = billing.create_featured_checkout_session(
				agency_id=self.agency.name,
				property_ids=self.featured_properties,
				start_date="2026-05-01",
				end_date="2026-05-07",
			)
			self.assertTrue(created.get("url"))
			completed = billing.complete_featured_checkout(
				session_id=created.get("session_id"),
				agency_id=self.agency.name,
			)
			self.assertTrue(completed.get("ok"))
			self.assertEqual(len(completed.get("activated_properties") or []), 2)

			second = billing.complete_featured_checkout(
				session_id=created.get("session_id"),
				agency_id=self.agency.name,
			)
			self.assertTrue(second.get("ok"))
			self.assertTrue(second.get("idempotent"))

		for property_name in self.featured_properties:
			doc = frappe.get_doc("Property", property_name)
			self.assertEqual(cint(doc.is_featured), 1)
			self.assertTrue(doc.featured_until)
			log_rows = frappe.get_all(
				"Property Featured Log",
				filters={
					"property": property_name,
					"event_type": "Activated",
					"source": "Billing",
				},
				pluck="name",
			)
			self.assertEqual(len(log_rows), 1)

	def test_expire_featured_properties_clears_window_and_logs(self):
		property_doc = frappe.get_doc(
			{
				"doctype": "Property",
				"title": f"Featured Expiry {self.suffix}",
				"listing_type": "Buy",
				"property_type": "Apartment",
				"price": 950000,
				"currency": "AED",
				"agent": self.agent.name,
				"agency": self.agency.name,
				"status": "Active",
				"completion_status": "Ready",
				"is_featured": 1,
				"featured_from": add_to_date(now_datetime(), days=-5, as_string=True),
				"featured_until": add_to_date(now_datetime(), minutes=-30, as_string=True),
			}
		).insert(ignore_permissions=True)
		self.featured_properties.append(property_doc.name)

		result = properties_api.expire_featured_properties()
		self.assertGreaterEqual(result.get("expired_count", 0), 1)

		property_doc.reload()
		self.assertEqual(cint(property_doc.is_featured), 0)
		self.assertFalse(property_doc.featured_from)
		self.assertFalse(property_doc.featured_until)

		logs = frappe.get_all(
			"Property Featured Log",
			filters={
				"property": property_doc.name,
				"event_type": "Expired",
				"source": "Scheduler",
			},
			pluck="name",
		)
		self.assertEqual(len(logs), 1)

	def test_list_featured_overdues_returns_amounts(self):
		frappe.set_user(self.user.name)
		due_date = add_days(today(), -5)
		invoice = frappe.get_doc(
			{
				"doctype": "Agency Billing Invoice",
				"agency": self.agency.name,
				"status": "Open",
				"currency": "AED",
				"invoice_date": add_days(today(), -10),
				"due_date": due_date,
				"billing_period_start": add_days(today(), -10),
				"billing_period_end": add_days(today(), -5),
				"items": [
					{
						"entry_type": "Addon",
						"addon": self.featured_addon.name,
						"description": "Featured dues",
						"quantity": 2,
						"rate": 600,
						"amount": 1200,
						"currency": "AED",
					}
				],
			}
		).insert(ignore_permissions=True)

		result = billing.list_featured_overdues(agency_id=self.agency.name)
		self.assertEqual(result.get("count"), 1)
		self.assertEqual(cint(result.get("total_overdue")), 1200)
		self.assertEqual((result.get("items") or [])[0].get("invoice"), invoice.name)


class TestAgencyTrialMaintenance(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.suffix = frappe.generate_hash(length=8)
		self.agency = frappe.get_doc(
			{
				"doctype": "Agency",
				"agency_name": f"Trial Agency {self.suffix}",
				"status": "Active",
				"email": f"trial-{self.suffix}@example.com",
				"phone": "+971500000002",
				"whatsapp_number": "+971500000002",
				"billing_status": "Not Configured",
				"trial_status": "Active",
				"is_on_trial": 1,
				"trial_start_date": "2026-01-01",
				"trial_end_date": "2026-01-10",
			}
		).insert(ignore_permissions=True)
		settings = frappe.get_single("Agency Billing Settings")
		settings.trial_grace_days = 0
		settings.flags.ignore_permissions = True
		settings.save()
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		if frappe.db.exists("Agency", self.agency.name):
			frappe.delete_doc("Agency", self.agency.name, ignore_permissions=True, force=1)
		frappe.db.commit()

	def test_trial_maintenance_marks_expired(self):
		out = billing.run_daily_agency_trial_maintenance("2026-01-15")
		self.assertGreaterEqual(out.get("expired", 0), 1)
		agency = frappe.get_doc("Agency", self.agency.name)
		self.assertEqual(agency.trial_status, "Expired")
		self.assertEqual(agency.billing_status, "Past Due")
