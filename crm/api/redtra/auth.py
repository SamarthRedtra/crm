from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.auth import LoginManager

from . import utils


@frappe.whitelist(methods=["POST"], allow_guest=True)
def register() -> dict[str, Any]:
	data = utils.get_request_json(["full_name", "email", "password"])
	email = data["email"].strip().lower()

	if frappe.db.exists("User", email):
		frappe.throw(_("Email {0} is already registered.").format(email), frappe.DuplicateEntryError)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": data["full_name"],
			"enabled": 1,
			"send_welcome_email": 0,
		}
	)
	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.new_password = data["password"]
	if phone := data.get("phone"):
		user.mobile_no = phone

	user.insert()
	user.add_roles("Customer")

	utils.ensure_customer_record(user.name, data["full_name"], email, data.get("phone"))

	frappe.response.http_status_code = 201
	return {"message": _("Registration successful.")}


@frappe.whitelist(methods=["POST"], allow_guest=True)
def login() -> dict[str, Any]:
	data = utils.get_request_json(["email", "password"])
	email = data["email"].strip()
	password = data["password"]

	login_manager = LoginManager()
	login_manager.authenticate(user=email, pwd=password)
	login_manager.post_login()

	token = utils.generate_jwt(login_manager.user)

	user_doc = frappe.get_doc("User", login_manager.user)
	return {
		"token": token,
		"user_id": login_manager.user,
		"full_name": user_doc.full_name,
	}


@frappe.whitelist()
@utils.require_jwt()
def logout() -> dict[str, Any]:
	auth = getattr(frappe.local, "redtra_auth", {})
	token = auth.get("token")
	payload = auth.get("payload") or {}
	if token and payload:
		utils.blacklist_token(token, payload.get("exp", 0))
	return {"message": _("Logged out successfully.")}


@frappe.whitelist()
@utils.require_jwt()
def get_profile() -> dict[str, Any]:
	user = utils.get_current_user()
	customer = utils.get_customer_by_user(user)
	user_doc = frappe.get_doc("User", user)

	if customer:
		return {
			"user_id": user,
			"full_name": customer.full_name,
			"email": customer.email,
			"phone": customer.phone,
			"whatsapp_number": customer.whatsapp_number,
			"preferred_city": customer.preferred_city,
		}

	return {
		"user_id": user,
		"full_name": user_doc.full_name,
		"email": user_doc.email or user_doc.user_email,
		"phone": user_doc.mobile_no,
	}


@frappe.whitelist()
@utils.require_jwt()
def update_profile() -> dict[str, Any]:
	data = utils.get_request_json()
	user = utils.get_current_user()
	customer = utils.get_customer_by_user(user)

	if not customer:
		utils.ensure_customer_record(
			user,
			data.get("full_name") or frappe.get_cached_value("User", user, "full_name"),
			data.get("email") or frappe.get_cached_value("User", user, "email"),
			data.get("phone"),
		)
		customer = utils.get_customer_by_user(user)

	customer.update(
		{
			"full_name": data.get("full_name") or customer.full_name,
			"email": data.get("email") or customer.email,
			"phone": data.get("phone") or customer.phone,
			"whatsapp_number": data.get("whatsapp_number") or customer.whatsapp_number,
			"preferred_city": data.get("preferred_city") or customer.preferred_city,
		}
	)
	customer.save(ignore_permissions=True)

	# keep user doc in sync
	user_doc = frappe.get_doc("User", user)
	if data.get("full_name"):
		user_doc.first_name = data.get("full_name")
	if data.get("email"):
		user_doc.email = data.get("email")
	if data.get("phone"):
		user_doc.mobile_no = data.get("phone")
	user_doc.save(ignore_permissions=True)

	return {"message": _("Profile updated successfully.")}

