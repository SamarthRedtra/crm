"""
Handle sid (session ID) from URL for CRM authentication.

When a user logs in via the Redtra API, they receive a sid in the response.
Visiting /crm?sid=xxx should authenticate them. This module ensures:
1. sid from URL is preserved in form_dict before session creation
2. A fallback endpoint /api/auth/set-session-from-sid for explicit cookie setting
3. GET /api/auth/get-sid to obtain a fresh SID when JWT is valid but SID expired
"""
from __future__ import annotations

from urllib.parse import quote

import frappe
from frappe import _

from . import utils


def _encode_redirect(path: str) -> str:
	return quote(path, safe="")


def ensure_sid_in_form_dict():
	"""
	Run early in request: ensure sid from URL query string is in form_dict
	before Session is created. Frappe's make_form_dict should include it,
	but we explicitly preserve it for /crm paths in case of routing quirks.
	"""
	request = getattr(frappe.local, "request", None)
	if not request:
		return

	path = (request.path or "").strip()
	if not path.startswith("/crm"):
		return

	sid_from_url = None
	if request.args:
		sid_from_url = request.args.get("sid")
	if not sid_from_url:
		return

	# Ensure form_dict has sid so Session.__init__ will use it (Session pops it)
	form_dict = getattr(frappe.local, "form_dict", None)
	if form_dict is not None:
		form_dict["sid"] = sid_from_url


@frappe.whitelist(allow_guest=True)
def set_session_from_sid():
	"""
	Endpoint: GET /api/auth/set-session-from-sid?sid=xxx&redirect=/crm
	Validates sid, sets cookie, redirects to /crm.
	"""
	sid = (frappe.form_dict.get("sid") or "").strip()
	redirect_to = (frappe.form_dict.get("redirect") or "/crm").strip() or "/crm"

	if not sid:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = f"/login?redirect-to={_encode_redirect(redirect_to)}"
		return

	# Validate sid by loading session data
	session_data = _get_session_data(sid)
	if not session_data or not session_data.get("user") or session_data.get("user") == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = f"/login?redirect-to={_encode_redirect(redirect_to)}"
		return

	# Set sid cookie so subsequent requests are authenticated
	from frappe.auth import get_expiry_in_seconds

	frappe.local.cookie_manager.set_cookie(
		"sid",
		sid,
		max_age=get_expiry_in_seconds(),
		httponly=True,
	)
	frappe.local.cookie_manager.set_cookie(
		"user_id",
		session_data.get("user", ""),
		max_age=get_expiry_in_seconds(),
	)

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = redirect_to


def _get_session_data(sid: str) -> dict | None:
	"""Load session data from cache or DB. Returns None if invalid/expired."""
	if not sid or sid == "Guest":
		return None

	# Try cache first
	data = frappe.cache().hget("session", sid)
	if data:
		return frappe._dict(data)

	# Try DB
	Sessions = frappe.qb.DocType("Sessions")
	row = (
		frappe.qb.from_(Sessions)
		.select(Sessions.user, Sessions.sessiondata, Sessions.lastupdate)
		.where(Sessions.sid == sid)
		.where(Sessions.lastupdate > frappe.sessions.get_expired_threshold())
		.limit(1)
	).run(as_dict=True)

	if not row:
		return None

	import json

	r = row[0]
	user = r.get("user")
	if not user or user == "Guest":
		return None

	return frappe._dict({"user": user, "data": json.loads(r.get("sessiondata") or "{}")})


@frappe.whitelist()
@utils.require_jwt()
def get_sid() -> dict[str, str]:
	"""
	Endpoint: GET /api/auth/get-sid (Bearer JWT required)
	Returns a fresh SID for the authenticated user. Use when SID expired but JWT is still valid.
	"""
	user = utils.get_current_user()
	if not user or user == "Guest":
		frappe.throw(_("Invalid authentication."), frappe.AuthenticationError)

	user_doc = frappe.get_cached_doc("User", user)
	if not user_doc.enabled:
		frappe.throw(_("User account is disabled."), frappe.PermissionError)

	sid = frappe.generate_hash()
	request_ip = getattr(frappe.local, "request_ip", None) or "127.0.0.1"
	user_agent = None
	if getattr(frappe.local, "request", None):
		user_agent = frappe.local.request.headers.get("User-Agent")

	from frappe.sessions import get_expiry_period

	session_data = frappe._dict({
		"user": user,
		"session_ip": request_ip,
		"user_agent": user_agent,
		"last_updated": frappe.utils.now(),
		"creation": frappe.utils.now(),
		"session_expiry": get_expiry_period(),
		"full_name": user_doc.full_name,
		"user_type": user_doc.user_type or "Website User",
	})

	# Build full session structure (matches Frappe Session.data)
	full_data = frappe._dict({
		"user": user,
		"sid": sid,
		"data": session_data,
	})

	Sessions = frappe.qb.DocType("Sessions")
	now = frappe.utils.now()
	(
		frappe.qb.into(Sessions)
		.columns(Sessions.sessiondata, Sessions.user, Sessions.lastupdate, Sessions.sid, Sessions.status)
		.insert(
			(
				frappe.as_json(session_data, indent=None, separators=(",", ":")),
				user,
				now,
				sid,
				"Active",
			)
		)
	).run()
	frappe.cache().hset("session", sid, full_data)
	frappe.db.commit()

	return {"sid": sid}
