from __future__ import annotations

from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import add_months, cint, get_datetime_str, now_datetime
from frappe.utils.password import update_password

from . import properties, utils


@frappe.whitelist(methods=["POST"], allow_guest=True)
def register() -> dict[str, Any]:
	data = utils.get_request_json(["full_name", "email", "password"])
	email = data["email"].strip().lower()
	is_agent = _coerce_bool(data.get("is_agent"))
	agent_id = (data.get("agent_id") or "").strip() or None

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
	if is_agent:
		utils.ensure_agent_role(user.name)
		_create_agent_record(user.name, data, agent_id)
	else:
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


@frappe.whitelist(methods=["POST"],allow_guest=True)
@utils.require_jwt()
def forgot_password() -> dict[str, Any]:
	data = utils.get_request_json(["email", "password", "new_password"])
	email = data["email"].strip().lower()
	new_password = data["password"]
	confirm_password = data["new_password"]

	if new_password != confirm_password:
		frappe.throw(_("Password and new password must match."), frappe.ValidationError)

	current_user = utils.get_current_user()
	if frappe.session.user != "Administrator" and current_user.lower() != email:
		frappe.throw(_("You can only reset your own password."), frappe.PermissionError)

	user_name = frappe.db.exists("User", {"name": email})
	if not user_name:
		frappe.response.http_status_code = 404
		frappe.throw(_("User not found."), frappe.DoesNotExistError)

	user_doc = frappe.get_doc("User", user_name)
	if user_doc.name == "Administrator":
		frappe.throw(_("Password reset for Administrator is not allowed."), frappe.PermissionError)
	if not user_doc.enabled:
		frappe.throw(_("User account is disabled."), frappe.PermissionError)

	user_doc.validate_reset_password()
	update_password(user=user_doc.name, pwd=new_password, logout_all_sessions=True)

	frappe.response.http_status_code = 200
	return {"message": _("Password has been reset successfully.")}


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
	user_doc = frappe.get_doc("User", user)
	customer = utils.get_customer_by_user(user)
	user_roles = set(frappe.get_roles(user))

	if "Agent" in user_roles:
		agent_name = frappe.db.get_value("Agent", {"user": user}, "name")
		if agent_name:
			agent_doc = frappe.get_doc("Agent", agent_name)
			start_of_day, end_of_day = _current_day_bounds()
			return _build_agent_profile(user_doc, agent_doc, start_of_day, end_of_day)

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
	user_roles = set(frappe.get_roles(user))

	if "Agent" in user_roles:
		_update_agent_details(user, data)

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
	if data.get("profile_image"):
		user_doc.user_image = data.get("profile_image")
	user_doc.save(ignore_permissions=True)

	return {"message": _("Profile updated successfully.")}


def _coerce_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return False
	if isinstance(value, (int, float)):
		return bool(value)
	if isinstance(value, str):
		return value.strip().lower() in {"1", "true", "yes", "y", "on"}
	return False


def _create_agent_record(user: str, data: dict[str, Any], agent_id: str | None = None):
	existing_agent_name = frappe.db.exists("Agent", {"user": user})
	if existing_agent_name:
		agent_doc = frappe.get_doc("Agent", existing_agent_name)
	else:
		agent_doc = None
		if agent_id:
			agent_by_dfd = frappe.db.get_value("Agent", {"dfd_registration_id": agent_id}, "name")
			if not agent_by_dfd:
				agent_by_name = frappe.db.exists("Agent", agent_id)
				if agent_by_name:
					agent_by_dfd = agent_by_name
			if agent_by_dfd:
				agent_doc = frappe.get_doc("Agent", agent_by_dfd)
				if agent_doc.user and agent_doc.user != user:
					frappe.throw(
						_("Agent {0} is already linked to another user.").format(agent_id),
						frappe.PermissionError,
					)
				agent_doc.user = user
		if agent_doc is None:
			agent_doc = frappe.get_doc({"doctype": "Agent", "user": user})
			agent_doc.flags.ignore_permissions = True

	agent_doc.phone = data.get("phone") or agent_doc.phone
	agent_doc.whatsapp_number = data.get("whatsapp_number") or data.get("phone") or agent_doc.whatsapp_number
	agent_doc.bio = data.get("bio") or agent_doc.bio
	if hasattr(agent_doc, "profile_image"):
		agent_doc.profile_image = data.get("profile_image") or agent_doc.profile_image
	if agent_id and not agent_doc.dfd_registration_id:
		agent_doc.dfd_registration_id = agent_id

	max_daily = data.get("max_daily_appointments")
	if max_daily is not None:
		agent_doc.max_daily_appointments = cint(max_daily)

	for kyc in data.get("kyc_documents") or []:
		if not isinstance(kyc, dict):
			continue
		document_type = kyc.get("document_type")
		document_file = kyc.get("document_file")
		if not document_type or not document_file:
			continue
		agent_doc.append(
			"kyc_documents",
			{
				"document_type": document_type,
				"document_file": document_file,
				"remarks": kyc.get("remarks"),
			},
		)

	if agent_doc.is_new():
		agent_doc.insert(ignore_permissions=True)
	else:
		agent_doc.save(ignore_permissions=True)


def _update_agent_details(user: str, data: dict[str, Any]):
	agent_name = frappe.db.get_value("Agent", {"user": user}, "name")
	if not agent_name:
		return

	agent_doc = frappe.get_doc("Agent", agent_name)
	updated = False

	if data.get("phone"):
		agent_doc.phone = data.get("phone")
		updated = True
	if "whatsapp_number" in data and data.get("whatsapp_number") is not None:
		agent_doc.whatsapp_number = data.get("whatsapp_number")
		updated = True

	about_me = data.get("about_me") or data.get("bio")
	if about_me is not None:
		agent_doc.bio = about_me
		updated = True

	if data.get("agent_id") and not agent_doc.dfd_registration_id:
		agent_doc.dfd_registration_id = data.get("agent_id")
		updated = True

	if data.get("profile_image") and hasattr(agent_doc, "profile_image"):
		agent_doc.profile_image = data.get("profile_image")
		updated = True

	if data.get("max_daily_appointments") is not None:
		agent_doc.max_daily_appointments = cint(data.get("max_daily_appointments"))
		updated = True

	if updated:
		agent_doc.save(ignore_permissions=True)


def _current_day_bounds() -> tuple[Any, Any]:
	now = now_datetime()
	start = now.replace(hour=0, minute=0, second=0, microsecond=0)
	end = start + timedelta(days=1)
	return start, end


def _build_agent_profile(user_doc, agent_doc, start_of_day, end_of_day) -> dict[str, Any]:
	properties_listed = _get_agent_properties(agent_doc.name)
	appointments_today = _get_agent_appointments_today(agent_doc.name, start_of_day, end_of_day)
	lead_stats = _get_agent_lead_stats(user_doc.name, start_of_day, end_of_day)

	return {
		"user_id": user_doc.name,
		"full_name": user_doc.full_name,
		"email": user_doc.email or user_doc.user_email,
		"phone": agent_doc.phone or user_doc.mobile_no,
		"whatsapp_number": agent_doc.whatsapp_number,
		"agent_profile": {
			"id": agent_doc.name,
			"status": agent_doc.status,
			"about_me": agent_doc.bio,
			"profile_image": getattr(agent_doc, "profile_image", None),
			"max_daily_appointments": agent_doc.max_daily_appointments,
		},
		"appointments_today": appointments_today,
		"properties": properties_listed,
		"lead_stats": lead_stats,
	}


def _get_agent_appointments_today(agent_name: str, start_of_day, end_of_day) -> list[dict[str, Any]]:
	appointments = frappe.get_all(
		"Property Appointment",
		filters={
			"agent": agent_name,
			"status": "Scheduled",
			"start_datetime": ["between", [get_datetime_str(start_of_day), get_datetime_str(end_of_day)]],
		},
		fields=["name", "start_datetime", "end_datetime", "property", "customer", "status"],
		order_by="start_datetime asc",
	)

	results: list[dict[str, Any]] = []
	for appt in appointments:
		property_id = appt.get("property")
		customer_id = appt.get("customer")
		property_title = frappe.db.get_value("Property", property_id, "title") if property_id else None
		customer_name = frappe.db.get_value("Customer", customer_id, "full_name") if customer_id else None
		results.append(
			{
				"id": appt.get("name"),
				"start": get_datetime_str(appt.get("start_datetime")),
				"end": get_datetime_str(appt.get("end_datetime")),
				"status": appt.get("status"),
				"property": {"id": property_id, "title": property_title},
				"customer": {"id": customer_id, "name": customer_name},
			}
		)
	return results


def _get_agent_properties(agent_name: str, limit: int = 20) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Property",
		filters={"agent": agent_name, "status": "Active"},
		fields=properties.SUMMARY_FIELDS,
		order_by="modified desc",
		limit=limit,
	)
	return [properties.serialize_property_summary(dict(row)) for row in rows]


def _get_agent_lead_stats(user: str, start_of_day, end_of_day) -> dict[str, Any]:
	filters = {"lead_owner": user}
	total = frappe.db.count("CRM Lead", filters)

	start_str = get_datetime_str(start_of_day)
	end_str = get_datetime_str(end_of_day)

	today_filters = {**filters, "creation": ["between", [start_str, end_str]]}
	today_count = frappe.db.count("CRM Lead", today_filters)

	last_month_start = add_months(start_str, -1)
	last_month_end = add_months(end_str, -1)
	last_month_filters = {
		**filters,
		"creation": ["between", [last_month_start, last_month_end]],
	}
	last_month_count = frappe.db.count("CRM Lead", last_month_filters)

	trend = None
	if last_month_count:
		trend = (today_count - last_month_count) / last_month_count

	return {
		"total": total,
		"today": today_count,
		"last_month_same_day": last_month_count,
		"trend_ratio": trend,
	}

