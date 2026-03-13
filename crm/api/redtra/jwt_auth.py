from __future__ import annotations

import frappe
from frappe import _

from . import utils


EXEMPT_PATHS = {
	"/api/auth/login",
	"/api/auth/register",
	"/api/auth/refresh",
	"/api/auth/set-session-from-sid",
	"/api/method/crm.api.redtra.auth.login",
	"/api/method/crm.api.redtra.auth.register",
}


def authenticate():
	"""Authenticate requests that present a Redtra JWT via the Authorization header."""
	if frappe.request is None:
		return

	if frappe.request.path in EXEMPT_PATHS:
		return

	auth_header = frappe.get_request_header("Authorization")
	if not auth_header:
		return

	parts = auth_header.split(" ", 1)
	if len(parts) != 2 or parts[0].lower() != "bearer":
		return

	token = parts[1].strip()
	if not token:
		return

	if utils.is_token_blacklisted(token):
		frappe.throw(_("Token has been revoked."), frappe.AuthenticationError)

	payload = utils.decode_jwt(token)
	user = payload.get("user")
	if not user:
		frappe.throw(_("Invalid authentication token."), frappe.AuthenticationError)

	frappe.set_user(user)
	login_manager = getattr(frappe.local, "login_manager", None)
	if login_manager:
		login_manager.user = user
		login_manager.resume = True

	frappe.local.redtra_auth = {"token": token, "payload": payload}

