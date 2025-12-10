from __future__ import annotations

import functools
import math
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Iterable

import jwt

import frappe
from frappe import _
from frappe.utils import cint


def get_jwt_secret() -> str:
	secret = (
		frappe.local.conf.get("redtra_jwt_secret")
		or frappe.local.conf.get("jwt_secret")
		or frappe.conf.get("redtra_jwt_secret")
		or frappe.conf.get("jwt_secret")
	)
	if not secret:
		frappe.throw(
			_("JWT secret is not configured. Set `redtra_jwt_secret` in site_config.json."),
			frappe.AuthenticationError,
		)
	return secret


def generate_jwt(user: str, expires_in_hours: int = 24) -> str:
	now = datetime.utcnow()
	payload = {
		"user": user,
		"iat": int(now.timestamp()),
		"exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
	}
	return jwt.encode(payload, get_jwt_secret(), algorithm="HS256")


def decode_jwt(token: str) -> dict[str, Any]:
	try:
		return jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
	except jwt.ExpiredSignatureError:
		frappe.throw(_("Session expired. Please login again."), exc=frappe.AuthenticationError)
	except jwt.InvalidTokenError:
		frappe.throw(_("Invalid authentication token."), exc=frappe.AuthenticationError)


def blacklist_token(token: str, expires_at: int):
	cache = frappe.cache()
	ttl = max(expires_at - int(datetime.utcnow().timestamp()), 0)
	cache.set_value(f"redtra_jwt_blacklist::{token}", 1, expires_in_sec=ttl)


def is_token_blacklisted(token: str) -> bool:
	return bool(frappe.cache().get_value(f"redtra_jwt_blacklist::{token}"))


def extract_bearer_token() -> str:
	auth_header = frappe.get_request_header("Authorization")
	if not auth_header or not auth_header.lower().startswith("bearer "):
		frappe.throw(_("Missing bearer token."), frappe.AuthenticationError)
	return auth_header.split(" ", 1)[1].strip()


def get_optional_bearer_token() -> str | None:
	auth_header = frappe.get_request_header("Authorization")
	if not auth_header or not auth_header.lower().startswith("bearer "):
		return None
	token = auth_header.split(" ", 1)[1].strip()
	return token or None


def require_jwt(roles: Iterable[str] | None = None) -> Callable:
	required_roles = set(roles or [])

	def decorator(func: Callable):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			token = extract_bearer_token()
			if is_token_blacklisted(token):
				frappe.throw(_("Token has been revoked."), frappe.AuthenticationError)

			payload = decode_jwt(token)
			user = payload.get("user")
			if not user:
				frappe.throw(_("Invalid authentication token."), frappe.AuthenticationError)

			previous_user = frappe.session.user
			frappe.set_user(user)
			frappe.local.redtra_auth = {"token": token, "payload": payload}

			try:
				if required_roles:
					user_roles = set(frappe.get_roles(user))
					if required_roles.isdisjoint(user_roles):
						frappe.throw(_("Insufficient permissions."), frappe.PermissionError)
				return func(*args, **kwargs)
			finally:
				frappe.set_user(previous_user)

		return wrapper

	return decorator


@contextmanager
def maybe_authenticate_jwt(roles: Iterable[str] | None = None):
	token = get_optional_bearer_token()
	if not token:
		yield None
		return

	if is_token_blacklisted(token):
		frappe.throw(_("Token has been revoked."), frappe.AuthenticationError)

	payload = decode_jwt(token)
	user = payload.get("user")
	if not user:
		frappe.throw(_("Invalid authentication token."), frappe.AuthenticationError)

	required_roles = set(roles or [])
	if required_roles:
		user_roles = set(frappe.get_roles(user))
		if required_roles.isdisjoint(user_roles):
			frappe.throw(_("Insufficient permissions."), frappe.PermissionError)

	previous_user = frappe.session.user
	had_previous_auth = hasattr(frappe.local, "redtra_auth")
	previous_auth = frappe.local.redtra_auth if had_previous_auth else None

	frappe.set_user(user)
	frappe.local.redtra_auth = {"token": token, "payload": payload}

	try:
		yield user
	finally:
		frappe.set_user(previous_user)
		if had_previous_auth:
			frappe.local.redtra_auth = previous_auth
		elif hasattr(frappe.local, "redtra_auth"):
			delattr(frappe.local, "redtra_auth")


def get_current_user() -> str:
	payload = getattr(frappe.local, "redtra_auth", {}).get("payload") or {}
	return payload.get("user") or frappe.session.user


def get_request_json(required_fields: Iterable[str] | None = None) -> dict[str, Any]:
	data = frappe.request.get_json() or {}
	required_fields = required_fields or []

	missing = [field for field in required_fields if not data.get(field)]
	if missing:
		frappe.throw(
			_("Missing required fields: {0}").format(", ".join(missing)),
			frappe.ValidationError,
		)
	return data


def get_paginated_list(
	doctype: str,
	filters: dict[str, Any] | list[list[Any]] | None = None,
	fields: list[str] | None = None,
	page: int | None = None,
	page_size: int | None = None,
	order_by: str | None = None,
) -> dict[str, Any]:
	page = max(1, cint(page or 1))
	page_size = cint(page_size or 20)
	page_size = max(1, min(page_size, 100))

	start = (page - 1) * page_size
	filters = filters or {}
	fields = fields or ["name"]
	order_by = order_by or "modified desc"

	items = frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		start=start,
		limit=page_size,
		order_by=order_by,
	)
	total_items = frappe.db.count(doctype, filters)
	total_pages = math.ceil(total_items / page_size) if page_size else 0

	return {
		"items": items,
		"page": page,
		"page_size": page_size,
		"total_items": total_items,
		"total_pages": total_pages,
	}


def ensure_customer_record(user: str, full_name: str, email: str, phone: str | None = None):
	if frappe.db.exists("Customer", {"user": user}):
		return

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"user": user,
			"full_name": full_name,
			"email": email,
			"phone": phone,
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()


def get_customer_by_user(user: str):
	customer_name = frappe.db.get_value("Customer", {"user": user})
	if customer_name:
		return frappe.get_doc("Customer", customer_name)
	return None


def ensure_agent_role(user: str):
	if "Agent" not in frappe.get_roles(user):
		doc = frappe.get_doc("User", user)
		doc.flags.ignore_permissions = True
		doc.add_roles("Agent")

