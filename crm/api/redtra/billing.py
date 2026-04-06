from __future__ import annotations

from collections import defaultdict
import hashlib
from typing import Any
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	cint,
	flt,
	get_first_day,
	get_last_day,
	get_url,
	getdate,
	now_datetime,
	today,
)

from . import utils


AGENCY_EDITABLE_FIELDS = [
	"agency_name",
	"email",
	"phone",
	"website",
	"brn_id",
	"address_line1",
	"address_line2",
	"city",
	"state",
	"country",
	"pincode",
	"description",
	"billing_contact_name",
	"billing_email",
	"billing_currency",
	"billing_start_date",
]

TEAM_EDITABLE_FIELDS = [
	"agency_role",
	"agent_level",
	"billable",
	"billing_start_date",
	"billing_end_date",
]

ZERO_DECIMAL_CURRENCIES = {
	"bif",
	"clp",
	"djf",
	"gnf",
	"jpy",
	"kmf",
	"krw",
	"mga",
	"pyg",
	"rwf",
	"ugx",
	"vnd",
	"vuv",
	"xaf",
	"xof",
	"xpf",
}


def _is_internal_manager(user: str | None = None) -> bool:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return user == "Administrator" or bool({"System Manager", "Sales Manager"} & roles)


def _require_internal_manager():
	if not _is_internal_manager():
		frappe.throw(_("Only CRM managers can access this action."), frappe.PermissionError)


def _get_agent_record(user: str | None = None) -> dict[str, Any] | None:
	user = user or frappe.session.user
	return frappe.db.get_value(
		"Agent",
		{"user": user},
		[
			"name",
			"user",
			"full_name",
			"email",
			"status",
			"agency",
			"agency_role",
			"agent_level",
			"billable",
			"billing_start_date",
			"billing_end_date",
		],
		as_dict=True,
	)


def get_agency_access_context(user: str | None = None, agency_id: str | None = None) -> dict[str, Any]:
	user = user or frappe.session.user
	agent = _get_agent_record(user)
	roles = list(frappe.get_roles(user))
	is_internal_manager = _is_internal_manager(user)

	agency_name = agency_id or (agent.get("agency") if agent else None)
	agency_doc = frappe.get_doc("Agency", agency_name) if agency_name and frappe.db.exists("Agency", agency_name) else None

	is_agency_member = bool(agent and agency_doc and agent.get("agency") == agency_doc.name)
	if agency_id and not (is_internal_manager or is_agency_member):
		frappe.throw(_("You do not have access to this agency."), frappe.PermissionError)

	agency_role = agent.get("agency_role") if is_agency_member and agent else ""
	is_agency_admin = agency_role == "Admin"
	is_agency_manager = agency_role in {"Admin", "Manager"}
	verification_status = agency_doc.verification_status if agency_doc and hasattr(agency_doc, "verification_status") else "Verified"
	trial_status = agency_doc.trial_status if agency_doc and hasattr(agency_doc, "trial_status") else "Not Started"
	is_on_trial = bool(cint(getattr(agency_doc, "is_on_trial", 0))) if agency_doc else False
	payment_mode = _get_payment_mode()
	billing_status = agency_doc.billing_status if agency_doc else None
	requires_billing_activation = bool(
		agency_doc
		and verification_status == "Verified"
		and agency_doc.onboarding_status == "Completed"
		and trial_status not in {"Active", "Grace"}
		and billing_status != "Active"
		and _is_billing_enabled()
	)

	return {
		"user": user,
		"roles": roles,
		"is_internal_manager": is_internal_manager,
		"agent": agent,
		"agent_name": agent.get("name") if agent else None,
		"agency": agency_doc.name if agency_doc else None,
		"agency_name": agency_doc.agency_name if agency_doc else None,
		"agency_role": agency_role or "",
		"is_agency_member": is_agency_member,
		"is_agency_admin": is_agency_admin,
		"is_agency_manager": is_agency_manager,
		"can_view_agency": bool(is_internal_manager or is_agency_member),
		"can_edit_agency_profile": bool(is_internal_manager or is_agency_manager),
		"can_manage_team": bool(is_internal_manager or is_agency_manager),
		"can_manage_billing": bool(is_internal_manager or is_agency_admin),
		"onboarding_status": agency_doc.onboarding_status if agency_doc else None,
		"onboarding_completed": bool(agency_doc and agency_doc.onboarding_status == "Completed"),
		"billing_status": billing_status,
		"payment_mode": payment_mode,
		"verification_status": verification_status,
		"verification_notes": getattr(agency_doc, "verification_notes", None) if agency_doc else None,
		"is_verified": verification_status == "Verified",
		"is_verification_pending": verification_status == "Pending Verification",
		"is_verification_rejected": verification_status == "Rejected",
		"is_on_trial": is_on_trial,
		"trial_status": trial_status,
		"trial_start_date": agency_doc.trial_start_date if agency_doc and hasattr(agency_doc, "trial_start_date") else None,
		"trial_end_date": agency_doc.trial_end_date if agency_doc and hasattr(agency_doc, "trial_end_date") else None,
		"trial_grace_end_date": agency_doc.trial_grace_end_date if agency_doc and hasattr(agency_doc, "trial_grace_end_date") else None,
		"requires_billing_activation": requires_billing_activation,
	}


def _require_agency_access(
	agency_id: str | None = None,
	*,
	require_profile: bool = False,
	require_team: bool = False,
	require_billing: bool = False,
) -> tuple[dict[str, Any], Any]:
	context = get_agency_access_context(agency_id=agency_id)
	if not context["agency"]:
		frappe.throw(_("No agency is linked to the current user."), frappe.PermissionError)
	if require_profile and not context["can_edit_agency_profile"]:
		frappe.throw(_("You do not have permission to update this agency."), frappe.PermissionError)
	if require_team and not context["can_manage_team"]:
		frappe.throw(_("You do not have permission to manage agency members."), frappe.PermissionError)
	if require_billing and not context["can_manage_billing"]:
		frappe.throw(_("You do not have permission to manage billing."), frappe.PermissionError)
	return context, frappe.get_doc("Agency", context["agency"])


def _get_billing_settings():
	try:
		return frappe.get_single("Agency Billing Settings")
	except frappe.DoesNotExistError:
		return None


def _is_billing_enabled() -> bool:
	settings = _get_billing_settings()
	if not settings:
		return False
	return bool(cint(getattr(settings, "billing_enabled", 0)))


def _get_payment_mode() -> str:
	settings = _get_billing_settings()
	if not settings:
		return "two_step"
	mode = (getattr(settings, "payment_mode", None) or "two_step").strip() or "two_step"
	if mode not in {"after_verification", "before_verification", "two_step"}:
		return "two_step"
	return mode


def _get_addon_charge_timing() -> str:
	settings = _get_billing_settings()
	if not settings:
		return "daily_accrual"
	timing = (getattr(settings, "addon_charge_timing", None) or "daily_accrual").strip() or "daily_accrual"
	if timing not in {"daily_accrual", "upfront_immediate"}:
		return "daily_accrual"
	return timing


def _get_trial_config() -> dict[str, Any]:
	settings = _get_billing_settings()
	if not settings:
		return {
			"enabled": False,
			"trial_days": 30,
			"trial_grace_days": 0,
			"requires_payment_method": False,
			"trial_max_agents": 0,
			"default_agent_level": None,
		}
	trial_days = max(cint(getattr(settings, "trial_days", 30) or 30), 1)
	trial_grace_days = max(cint(getattr(settings, "trial_grace_days", 0) or 0), 0)
	trial_max_agents = max(cint(getattr(settings, "trial_max_agents", 0) or 0), 0) if settings else 0
	default_agent_level = getattr(settings, "default_agent_level", None) if settings else None
	return {
		"enabled": bool(cint(getattr(settings, "trial_enabled", 0))),
		"trial_days": trial_days,
		"trial_grace_days": trial_grace_days,
		"requires_payment_method": bool(cint(getattr(settings, "trial_requires_payment_method", 0))),
		"trial_max_agents": trial_max_agents,
		"default_agent_level": default_agent_level,
	}


def validate_trial_agent_quota(agency_name: str) -> None:
	"""Block new Agent rows when agency is on trial and trial_max_agents is reached."""
	if not agency_name or not frappe.db.exists("Agency", agency_name):
		return
	agency_doc = frappe.get_doc("Agency", agency_name)
	trial_cfg = _get_trial_config()
	if not trial_cfg["enabled"]:
		return
	if (agency_doc.trial_status or "") not in {"Active", "Grace"}:
		return
	max_agents = cint(trial_cfg.get("trial_max_agents") or 0)
	if max_agents <= 0:
		return
	current = frappe.db.count("Agent", {"agency": agency_name})
	if current >= max_agents:
		frappe.throw(
			_("This agency has reached the maximum of {0} agents allowed during the trial. Contact CRM support.").format(
				max_agents
			),
			frappe.ValidationError,
		)


def get_default_agent_level_for_new_agent() -> str | None:
	settings = _get_billing_settings()
	if settings and getattr(settings, "default_agent_level", None):
		dl = settings.default_agent_level
		if dl and frappe.db.exists("Agent Level", dl):
			return dl
	rows = frappe.get_all(
		"Agent Level",
		filters={"active": 1},
		order_by="sort_order asc, level_name asc",
		limit=1,
		pluck="name",
	)
	return rows[0] if rows else None


def _agency_waives_daily_billing_during_trial(agency_doc) -> bool:
	if (getattr(agency_doc, "trial_status", None) or "") not in {"Active", "Grace"}:
		return False
	return bool(cint(getattr(agency_doc, "is_on_trial", 0)))


def _require_billing_enabled():
	if not _is_billing_enabled():
		frappe.throw(_("Agency billing is disabled in Agency Billing Settings."))


def _get_default_currency(agency_doc=None) -> str:
	if agency_doc and agency_doc.billing_currency:
		return agency_doc.billing_currency
	settings = _get_billing_settings()
	if settings and settings.default_currency:
		return settings.default_currency
	fcrm_currency = frappe.db.get_single_value("FCRM Settings", "currency")
	return fcrm_currency or "AED"


def _stripe_enabled() -> bool:
	settings = _get_billing_settings()
	if not settings:
		return False
	return bool(settings.get_password("stripe_secret_key", raise_exception=False))


def _get_stripe_publishable_key() -> str | None:
	settings = _get_billing_settings()
	if not settings or not _stripe_enabled():
		return None
	key = (getattr(settings, "stripe_publishable_key", None) or "").strip()
	return key or None


def _get_period_bounds(target_date: str | None = None) -> tuple[str, str]:
	target = getdate(target_date or today())
	return str(get_first_day(target)), str(get_last_day(target))


def _parse_payload(data: str | dict[str, Any] | None) -> dict[str, Any]:
	if data is None:
		return utils.get_request_json()
	if isinstance(data, dict):
		return data
	return frappe.parse_json(data) or {}


def _serialize_agent_level(level: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": level.get("name"),
		"level_name": level.get("level_name"),
		"daily_rate": flt(level.get("daily_rate")),
		"currency": level.get("currency"),
		"active": cint(level.get("active")),
		"sort_order": cint(level.get("sort_order") or 0),
		"description": level.get("description"),
	}


def _serialize_billing_addon(addon: dict[str, Any]) -> dict[str, Any]:
	r = flt(addon.get("rate"))
	return {
		"name": addon.get("name"),
		"addon_name": addon.get("addon_name"),
		"pricing_model": addon.get("pricing_model"),
		"rate": r,
		"effective_rate": r if r > 0 else None,
		"currency": addon.get("currency"),
		"unit_label": addon.get("unit_label"),
		"active": cint(addon.get("active")),
		"sort_order": cint(addon.get("sort_order") or 0),
		"description": addon.get("description"),
	}


def _serialize_agency_addon_row(row) -> dict[str, Any]:
	addon_meta = None
	if row.addon and frappe.db.exists("Billing Addon", row.addon):
		addon_meta = frappe.db.get_value(
			"Billing Addon",
			row.addon,
			["addon_name", "pricing_model", "rate", "currency", "unit_label", "active"],
			as_dict=True,
		)
	return {
		"name": row.name,
		"addon": row.addon,
		"addon_name": addon_meta.get("addon_name") if addon_meta else row.addon,
		"pricing_model": addon_meta.get("pricing_model") if addon_meta else None,
		"catalog_rate": flt(addon_meta.get("rate")) if addon_meta else 0,
		"currency": addon_meta.get("currency") if addon_meta else None,
		"unit_label": addon_meta.get("unit_label") if addon_meta else None,
		"active": cint(addon_meta.get("active")) if addon_meta else 0,
		"quantity": flt(row.quantity or 0),
		"custom_rate": flt(row.custom_rate) if row.custom_rate else None,
		"enabled": cint(row.enabled),
	}


def _serialize_team_member(agent: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": agent.get("name"),
		"user": agent.get("user"),
		"full_name": agent.get("full_name"),
		"email": agent.get("email"),
		"status": agent.get("status"),
		"agency_role": agent.get("agency_role") or "",
		"agent_level": agent.get("agent_level"),
		"billable": cint(agent.get("billable")),
		"billing_start_date": agent.get("billing_start_date"),
		"billing_end_date": agent.get("billing_end_date"),
	}


def _serialize_invoice(invoice_doc, include_items: bool = True) -> dict[str, Any]:
	if isinstance(invoice_doc, dict):
		doc = invoice_doc
		items = doc.get("items") or []
	else:
		doc = invoice_doc.as_dict()
		items = invoice_doc.items or []

	data = {
		"name": doc.get("name"),
		"agency": doc.get("agency"),
		"status": doc.get("status"),
		"trial_waived": cint(doc.get("trial_waived") or 0),
		"currency": doc.get("currency"),
		"invoice_date": doc.get("invoice_date"),
		"due_date": doc.get("due_date"),
		"billing_period_start": doc.get("billing_period_start"),
		"billing_period_end": doc.get("billing_period_end"),
		"subtotal": flt(doc.get("subtotal")),
		"total": flt(doc.get("total")),
		"stripe_invoice_id": doc.get("stripe_invoice_id"),
		"stripe_status": doc.get("stripe_status"),
		"stripe_hosted_invoice_url": doc.get("stripe_hosted_invoice_url"),
		"paid_on": doc.get("paid_on"),
		"error_message": doc.get("error_message"),
	}
	if include_items:
		data["items"] = [
			{
				"name": row.get("name") if isinstance(row, dict) else row.name,
				"entry_type": row.get("entry_type") if isinstance(row, dict) else row.entry_type,
				"description": row.get("description") if isinstance(row, dict) else row.description,
				"agent": row.get("agent") if isinstance(row, dict) else row.agent,
				"agent_level": row.get("agent_level") if isinstance(row, dict) else row.agent_level,
				"addon": row.get("addon") if isinstance(row, dict) else row.addon,
				"quantity": flt(row.get("quantity") if isinstance(row, dict) else row.quantity),
				"rate": flt(row.get("rate") if isinstance(row, dict) else row.rate),
				"amount": flt(row.get("amount") if isinstance(row, dict) else row.amount),
			}
			for row in items
		]
	return data


def _serialize_saved_payment_method(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": row.get("name"),
		"agency": row.get("agency"),
		"stripe_customer_id": row.get("stripe_customer_id"),
		"stripe_payment_method_id": row.get("stripe_payment_method_id"),
		"type": row.get("type"),
		"brand": row.get("brand"),
		"last4": row.get("last4"),
		"exp_month": cint(row.get("exp_month") or 0),
		"exp_year": cint(row.get("exp_year") or 0),
		"is_default": cint(row.get("is_default") or 0),
		"status": row.get("status") or "Active",
		"added_on": row.get("added_on"),
		"detached_on": row.get("detached_on"),
	}


def _list_saved_payment_methods_internal(agency_name: str, include_detached: bool = False) -> list[dict[str, Any]]:
	filters: dict[str, Any] = {"agency": agency_name}
	if not include_detached:
		filters["status"] = "Active"
	rows = frappe.get_all(
		"Agency Payment Method",
		filters=filters,
		fields=[
			"name",
			"agency",
			"stripe_customer_id",
			"stripe_payment_method_id",
			"type",
			"brand",
			"last4",
			"exp_month",
			"exp_year",
			"is_default",
			"status",
			"added_on",
			"detached_on",
		],
		order_by="is_default desc, modified desc",
	)
	return [_serialize_saved_payment_method(row) for row in rows]


def _summarize_accruals(accruals: list[dict[str, Any]]) -> list[dict[str, Any]]:
	grouped: dict[tuple[str, str, str, str, float], dict[str, Any]] = {}
	for row in accruals:
		key = (
			row.get("entry_type") or "",
			row.get("description") or "",
			row.get("agent") or "",
			row.get("addon") or "",
			flt(row.get("rate") or 0),
		)
		group = grouped.setdefault(
			key,
			{
				"entry_type": row.get("entry_type"),
				"description": row.get("description"),
				"agent": row.get("agent"),
				"addon": row.get("addon"),
				"quantity": 0,
				"rate": flt(row.get("rate") or 0),
				"amount": 0,
				"currency": row.get("currency"),
			},
		)
		group["quantity"] += flt(row.get("quantity") or 0)
		group["amount"] += flt(row.get("amount") or 0)
	return list(grouped.values())


def _get_open_period_summary(agency_name: str) -> dict[str, Any]:
	period_start, period_end = _get_period_bounds()
	accruals = frappe.get_all(
		"Agency Billing Accrual",
		filters={
			"agency": agency_name,
			"status": "Open",
			"billing_period_start": period_start,
			"billing_period_end": period_end,
		},
		fields=["name", "entry_type", "description", "agent", "addon", "quantity", "rate", "amount", "currency"],
		order_by="posting_date asc",
	)
	return {
		"period_start": period_start,
		"period_end": period_end,
		"currency": accruals[0]["currency"] if accruals else _get_default_currency(frappe.get_doc("Agency", agency_name)),
		"total_amount": flt(sum(flt(row["amount"]) for row in accruals)),
		"entry_count": len(accruals),
		"items": _summarize_accruals(accruals),
	}


def _get_agency_team(agency_name: str) -> list[dict[str, Any]]:
	members = frappe.get_all(
		"Agent",
		filters={"agency": agency_name},
		fields=[
			"name",
			"user",
			"full_name",
			"email",
			"status",
			"agency_role",
			"agent_level",
			"billable",
			"billing_start_date",
			"billing_end_date",
		],
		order_by="full_name asc",
	)
	return [_serialize_team_member(row) for row in members]


def _list_invoices_internal(agency_name: str, limit: int = 12) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		"Agency Billing Invoice",
		filters={"agency": agency_name},
		fields=[
			"name",
			"agency",
			"status",
			"currency",
			"invoice_date",
			"due_date",
			"billing_period_start",
			"billing_period_end",
			"subtotal",
			"total",
			"stripe_invoice_id",
			"stripe_status",
			"stripe_hosted_invoice_url",
			"paid_on",
			"error_message",
		],
		order_by="invoice_date desc, creation desc",
		limit=limit,
	)
	return [_serialize_invoice(row, include_items=False) for row in rows]


def _serialize_agency(agency_doc) -> dict[str, Any]:
	return {
		"name": agency_doc.name,
		"agency_name": agency_doc.agency_name,
		"status": agency_doc.status,
		"email": agency_doc.email,
		"phone": agency_doc.phone,
		"website": agency_doc.website,
		"brn_id": agency_doc.brn_id,
		"address_line1": agency_doc.address_line1,
		"address_line2": agency_doc.address_line2,
		"city": agency_doc.city,
		"state": agency_doc.state,
		"country": agency_doc.country,
		"pincode": agency_doc.pincode,
		"description": agency_doc.description,
		"logo": agency_doc.logo,
		"billing_contact_name": agency_doc.billing_contact_name,
		"billing_email": agency_doc.billing_email,
		"billing_currency": agency_doc.billing_currency or _get_default_currency(agency_doc),
		"billing_start_date": agency_doc.billing_start_date,
		"billing_status": agency_doc.billing_status,
		"onboarding_status": agency_doc.onboarding_status,
		"verification_status": getattr(agency_doc, "verification_status", "Verified"),
		"verification_notes": getattr(agency_doc, "verification_notes", None),
		"verified_on": getattr(agency_doc, "verified_on", None),
		"verified_by": getattr(agency_doc, "verified_by", None),
		"is_on_trial": cint(getattr(agency_doc, "is_on_trial", 0)),
		"trial_status": getattr(agency_doc, "trial_status", "Not Started"),
		"trial_start_date": getattr(agency_doc, "trial_start_date", None),
		"trial_end_date": getattr(agency_doc, "trial_end_date", None),
		"trial_grace_end_date": getattr(agency_doc, "trial_grace_end_date", None),
		"stripe_customer_id": agency_doc.stripe_customer_id,
		"stripe_default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		"billing_addons": [_serialize_agency_addon_row(row) for row in agency_doc.billing_addons or []],
	}


def _normalize_addon_input_rows(rows: list[Any] | None) -> dict[str, dict[str, Any]]:
	output: dict[str, dict[str, Any]] = {}
	for row in rows or []:
		addon = (row.get("addon") if isinstance(row, dict) else getattr(row, "addon", None)) or ""
		if not addon:
			continue
		quantity_raw = row.get("quantity") if isinstance(row, dict) else getattr(row, "quantity", None)
		custom_rate_raw = row.get("custom_rate") if isinstance(row, dict) else getattr(row, "custom_rate", None)
		enabled_raw = row.get("enabled") if isinstance(row, dict) else getattr(row, "enabled", 1)
		output[addon] = {
			"addon": addon,
			"quantity": flt(quantity_raw or 0),
			"custom_rate": flt(custom_rate_raw) if custom_rate_raw not in (None, "") else None,
			"enabled": cint(enabled_raw),
		}
	return output


def _effective_addon_rate(addon_doc, row: dict[str, Any]) -> float:
	custom_rate = row.get("custom_rate")
	if custom_rate not in (None, ""):
		custom_rate = flt(custom_rate)
		if custom_rate > 0:
			return custom_rate
	return flt(addon_doc.rate or 0)


def _collect_upfront_addon_deltas(
	*,
	agency_name: str,
	existing_rows: dict[str, dict[str, Any]],
	new_rows: dict[str, dict[str, Any]],
	effective_date: str,
) -> list[dict[str, Any]]:
	deltas: list[dict[str, Any]] = []
	for addon_name, new_row in new_rows.items():
		if not cint(new_row.get("enabled")):
			continue
		if not frappe.db.exists("Billing Addon", addon_name):
			continue
		addon_doc = frappe.get_doc("Billing Addon", addon_name)
		if not cint(addon_doc.active):
			continue
		if addon_doc.pricing_model not in {"Daily Fixed", "Monthly Fixed"}:
			continue

		prev = existing_rows.get(addon_name) or {}
		old_enabled = cint(prev.get("enabled"))
		old_qty = flt(prev.get("quantity") or 0) if old_enabled else 0
		new_qty = flt(new_row.get("quantity") or 0)
		if new_qty <= 0:
			continue

		old_rate = _effective_addon_rate(addon_doc, prev) if old_enabled else 0
		new_rate = _effective_addon_rate(addon_doc, new_row)
		if new_rate <= 0:
			continue

		old_total = old_qty * old_rate
		new_total = new_qty * new_rate
		amount_delta = flt(new_total - old_total)
		if amount_delta <= 0:
			continue

		charge_key = (
			f"addon_upfront::{agency_name}::{addon_doc.name}::{effective_date}"
			f"::old={old_qty:.6f}@{old_rate:.6f}::new={new_qty:.6f}@{new_rate:.6f}"
		)
		deltas.append(
			{
				"addon": addon_doc.name,
				"addon_name": addon_doc.addon_name,
				"currency": addon_doc.currency,
				"amount_delta": amount_delta,
				"old_quantity": old_qty,
				"new_quantity": new_qty,
				"old_rate": old_rate,
				"new_rate": new_rate,
				"charge_key": charge_key,
				"description": f"Upfront charge for {addon_doc.addon_name} ({addon_doc.pricing_model})",
			}
		)
	return deltas


def _create_upfront_addon_invoice(
	*,
	agency_doc,
	effective_date: str,
	delta: dict[str, Any],
	accrual_doc,
):
	settings = _get_billing_settings() or frappe._dict(invoice_due_days=7)
	invoice_doc = frappe.get_doc(
		{
			"doctype": "Agency Billing Invoice",
			"agency": agency_doc.name,
			"status": "Draft",
			"currency": delta.get("currency") or agency_doc.billing_currency or _get_default_currency(agency_doc),
			"invoice_date": effective_date,
			"due_date": add_days(effective_date, cint(settings.invoice_due_days or 7)),
			"billing_period_start": effective_date,
			"billing_period_end": effective_date,
			"items": [
				{
					"entry_type": "Addon",
					"description": delta["description"],
					"addon": delta["addon"],
					"quantity": 1,
					"rate": flt(delta["amount_delta"]),
					"amount": flt(delta["amount_delta"]),
					"source_accrual": accrual_doc.name,
				}
			],
		}
	)
	invoice_doc.flags.ignore_permissions = True
	invoice_doc.insert()
	frappe.db.set_value(
		"Agency Billing Accrual",
		accrual_doc.name,
		{"invoice": invoice_doc.name, "status": "Invoiced"},
		update_modified=False,
	)
	return invoice_doc


def _charge_addons_upfront(agency_doc, addon_deltas: list[dict[str, Any]], effective_date: str) -> dict[str, Any]:
	result: dict[str, Any] = {"attempted": 0, "charged": 0, "failed": 0, "invoices": [], "errors": []}
	if not addon_deltas:
		return result
	if _agency_waives_daily_billing_during_trial(agency_doc):
		result["skipped"] = "trial_waived"
		return result

	for delta in addon_deltas:
		result["attempted"] += 1
		accrual_name = frappe.db.get_value("Agency Billing Accrual", {"accrual_key": delta["charge_key"]}, "name")
		invoice_doc = None
		if accrual_name:
			accrual_doc = frappe.get_doc("Agency Billing Accrual", accrual_name)
			if accrual_doc.invoice and frappe.db.exists("Agency Billing Invoice", accrual_doc.invoice):
				invoice_doc = frappe.get_doc("Agency Billing Invoice", accrual_doc.invoice)
		else:
			accrual_doc = _ensure_accrual(
				{
					"agency": agency_doc.name,
					"posting_date": effective_date,
					"billing_period_start": effective_date,
					"billing_period_end": effective_date,
					"entry_type": "Addon",
					"addon": delta["addon"],
					"quantity": 1,
					"rate": flt(delta["amount_delta"]),
					"currency": delta.get("currency") or agency_doc.billing_currency or _get_default_currency(agency_doc),
					"description": delta["description"],
					"status": "Open",
					"accrual_key": delta["charge_key"],
					"external_reference": delta["charge_key"],
				}
			)
			if accrual_doc:
				invoice_doc = _create_upfront_addon_invoice(
					agency_doc=agency_doc,
					effective_date=effective_date,
					delta=delta,
					accrual_doc=accrual_doc,
				)
			else:
				continue

		if not invoice_doc:
			continue
		if not _stripe_enabled():
			invoice_doc.status = "Failed"
			invoice_doc.error_message = "Stripe is not configured for immediate upfront addon charging."
			invoice_doc.flags.ignore_permissions = True
			invoice_doc.save()
			result["failed"] += 1
			result["errors"].append({"addon": delta["addon"], "invoice": invoice_doc.name, "error": invoice_doc.error_message})
			result["invoices"].append(_serialize_invoice(invoice_doc))
			continue

		try:
			invoice_doc = _sync_invoice_to_stripe(invoice_doc)
			result["charged"] += 1
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Upfront addon Stripe charge failed")
			invoice_doc.reload()
			invoice_doc.status = "Failed"
			invoice_doc.error_message = "Immediate Stripe charge failed for upfront addon billing."
			invoice_doc.flags.ignore_permissions = True
			invoice_doc.save()
			result["failed"] += 1
			result["errors"].append({"addon": delta["addon"], "invoice": invoice_doc.name, "error": invoice_doc.error_message})
		result["invoices"].append(_serialize_invoice(invoice_doc))
	return result


@frappe.whitelist()
def get_session_agency_context(agency_id: str | None = None) -> dict[str, Any]:
	return get_agency_access_context(agency_id=agency_id)


@frappe.whitelist(allow_guest=True)
def public_billing_preview() -> dict[str, Any]:
	"""Non-secret billing defaults for public registration pages (no Stripe keys).

	Includes active Agent Level and Billing Addon catalog rows so signup can show list prices.
	"""
	settings = _get_billing_settings()
	trial = _get_trial_config()
	currency = "USD"
	if settings and getattr(settings, "default_currency", None):
		currency = settings.default_currency
	# Catalog is public marketing data; same lists as agency management (active only).
	try:
		agent_levels = _list_agent_levels(active_only=1)
	except Exception:
		agent_levels = []
	# Canonical base rate: first active row (legacy sites may still have multiple rows until migrate).
	agent_level = agent_levels[0] if agent_levels else None
	agent_levels = [agent_level] if agent_level else []
	try:
		billing_addons = _list_billing_addons(active_only=1)
	except Exception:
		billing_addons = []
	return {
		"billing_enabled": _is_billing_enabled(),
		"payment_mode": _get_payment_mode(),
		"trial_enabled": trial["enabled"],
		"trial_days": trial["trial_days"],
		"trial_grace_days": trial["trial_grace_days"],
		"trial_requires_payment_method": trial["requires_payment_method"],
		"trial_max_agents": trial.get("trial_max_agents", 0),
		"default_currency": currency,
		"agent_level": agent_level,
		"agent_levels": agent_levels,
		"billing_addons": billing_addons,
	}


@frappe.whitelist()
def get_agency_management_data(agency_id: str | None = None) -> dict[str, Any]:
	context, agency_doc = _require_agency_access(agency_id=agency_id)
	trial_config = _get_trial_config()
	return {
		"context": context,
		"agency": _serialize_agency(agency_doc),
		"team_members": _get_agency_team(agency_doc.name),
		"current_period": _get_open_period_summary(agency_doc.name),
		"invoices": _list_invoices_internal(agency_doc.name),
		"available_addons": _list_billing_addons(active_only=1),
		"available_levels": _list_agent_levels(active_only=1),
		"stripe_enabled": _stripe_enabled(),
		"stripe_publishable_key": _get_stripe_publishable_key(),
		"billing_enabled": _is_billing_enabled(),
		"payment_mode": _get_payment_mode(),
		"trial_config": trial_config,
		"saved_payment_methods": _list_saved_payment_methods_internal(agency_doc.name),
	}


@frappe.whitelist()
def list_agency_invoices(agency_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
	context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	del context
	return _list_invoices_internal(agency_doc.name, limit=max(1, min(cint(limit or 20), 100)))


@frappe.whitelist(methods=["POST"])
def update_current_agency_profile(agency_id: str | None = None, data: str | None = None) -> dict[str, Any]:
	context, agency_doc = _require_agency_access(agency_id=agency_id, require_profile=True)
	payload = _parse_payload(data)
	upfront_charge_result = None
	existing_addons_snapshot = _normalize_addon_input_rows(agency_doc.billing_addons or [])
	updated_addon_rows: list[dict[str, Any]] = []

	for fieldname in AGENCY_EDITABLE_FIELDS:
		if fieldname in payload:
			agency_doc.set(fieldname, payload.get(fieldname))

	if "billing_addons" in payload and context["can_manage_billing"]:
		_require_billing_enabled()
		existing_addon_rows = {r.addon: r for r in (agency_doc.billing_addons or [])}
		agency_doc.set("billing_addons", [])
		for row in payload.get("billing_addons") or []:
			if not row.get("addon"):
				continue
			addon_name = row.get("addon")
			if not frappe.db.exists("Billing Addon", addon_name):
				frappe.throw(_("Billing addon {0} was not found.").format(addon_name))
			quantity = flt(row.get("quantity") or 1)
			if quantity <= 0:
				frappe.throw(_("Billing addon quantity must be greater than zero."))
			custom_rate = None
			if _is_internal_manager():
				if row.get("custom_rate") not in (None, ""):
					custom_rate = flt(row.get("custom_rate"))
					if custom_rate < 0:
						frappe.throw(_("Custom addon rate cannot be negative."))
			else:
				prev = existing_addon_rows.get(addon_name)
				custom_rate = prev.custom_rate if prev and prev.custom_rate not in (None, 0) else None
			agency_doc.append(
				"billing_addons",
				{
					"addon": addon_name,
					"quantity": quantity,
					"custom_rate": custom_rate,
					"enabled": cint(row.get("enabled", 1)),
				},
			)
			updated_addon_rows.append(
				{
					"addon": addon_name,
					"quantity": quantity,
					"custom_rate": custom_rate,
					"enabled": cint(row.get("enabled", 1)),
				}
			)

	if agency_doc.onboarding_status == "Not Started":
		agency_doc.onboarding_status = "In Progress"

	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	if (
		"billing_addons" in payload
		and context["can_manage_billing"]
		and _get_addon_charge_timing() == "upfront_immediate"
	):
		effective_date = str(getdate(today()))
		addon_deltas = _collect_upfront_addon_deltas(
			agency_name=agency_doc.name,
			existing_rows=existing_addons_snapshot,
			new_rows=_normalize_addon_input_rows(updated_addon_rows),
			effective_date=effective_date,
		)
		upfront_charge_result = _charge_addons_upfront(agency_doc, addon_deltas, effective_date=effective_date)
		if upfront_charge_result.get("failed"):
			_create_agency_audit_comment(
				agency_doc.name,
				_("Upfront addon charge failures detected: {0}").format(
					", ".join(err.get("invoice") or err.get("addon") or "unknown" for err in upfront_charge_result.get("errors") or [])
				),
			)

	response = {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}
	if upfront_charge_result is not None:
		response["upfront_addon_charges"] = upfront_charge_result
	return response


@frappe.whitelist(methods=["POST"])
def complete_agency_onboarding(agency_id: str | None = None) -> dict[str, Any]:
	context, agency_doc = _require_agency_access(agency_id=agency_id, require_profile=True)
	if not agency_doc.billing_email:
		frappe.throw(_("Billing email is required to complete onboarding."))
	if not agency_doc.billing_contact_name:
		frappe.throw(_("Billing contact name is required to complete onboarding."))
	if _is_billing_enabled() and _get_payment_mode() == "before_verification" and not _has_billing_setup(agency_doc):
		frappe.throw(_("Billing setup is required before verification in the current payment mode."))
	if _get_trial_config()["requires_payment_method"] and not _has_billing_setup(agency_doc):
		frappe.throw(_("A payment method is required before completing onboarding."))

	agency_doc.onboarding_status = "Completed"
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	_create_agency_audit_comment(
		agency_doc.name,
		_("Agency onboarding completed by {0}.").format(frappe.session.user),
	)

	return {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist(methods=["POST"])
def approve_agency_verification(
	agency_id: str,
	notes: str | None = None,
	start_trial: int = 1,
) -> dict[str, Any]:
	_require_internal_manager()
	if not frappe.db.exists("Agency", agency_id):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	agency_doc = frappe.get_doc("Agency", agency_id)
	if _is_billing_enabled() and _get_payment_mode() == "before_verification" and not _has_billing_setup(agency_doc):
		frappe.throw(_("Billing setup is required before approving verification in current payment mode."))
	if _get_trial_config()["requires_payment_method"] and not _has_billing_setup(agency_doc):
		frappe.throw(_("A payment method is required before approving verification."))

	agency_doc.verification_status = "Verified"
	agency_doc.verification_notes = notes or agency_doc.verification_notes
	agency_doc.verified_by = frappe.session.user
	agency_doc.verified_on = now_datetime()

	if cint(start_trial) and _get_trial_config()["enabled"]:
		if (agency_doc.trial_status or "Not Started") in {"Not Started", "Expired"}:
			_start_agency_trial(agency_doc)

	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	_create_agency_audit_comment(
		agency_doc.name,
		_("Agency verification approved by {0}. Trial started: {1}.").format(
			frappe.session.user,
			"yes" if cint(start_trial) and _get_trial_config()["enabled"] else "no",
		),
	)

	return {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist(methods=["POST"])
def reject_agency_verification(agency_id: str, notes: str | None = None) -> dict[str, Any]:
	_require_internal_manager()
	if not frappe.db.exists("Agency", agency_id):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)

	agency_doc = frappe.get_doc("Agency", agency_id)
	agency_doc.verification_status = "Rejected"
	agency_doc.verification_notes = notes or agency_doc.verification_notes
	agency_doc.verified_by = None
	agency_doc.verified_on = None
	if agency_doc.trial_status in {"Active", "Grace"}:
		agency_doc.trial_status = "Expired"
		agency_doc.is_on_trial = 0
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	_create_agency_audit_comment(
		agency_doc.name,
		_("Agency verification rejected by {0}. Notes: {1}").format(frappe.session.user, notes or ""),
	)

	return {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist(methods=["POST"])
def request_agency_reverification(agency_id: str | None = None, notes: str | None = None) -> dict[str, Any]:
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_profile=True)
	agency_doc.verification_status = "Pending Verification"
	if notes:
		agency_doc.verification_notes = notes
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	_create_agency_audit_comment(
		agency_doc.name,
		_("Agency re-verification requested by {0}. Notes: {1}").format(frappe.session.user, notes or ""),
	)

	return {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist(methods=["POST"])
def activate_agency_paid_plan(agency_id: str | None = None) -> dict[str, Any]:
	if _is_internal_manager():
		if not agency_id:
			frappe.throw(_("Agency ID is required."))
		if not frappe.db.exists("Agency", agency_id):
			frappe.throw(_("Agency not found."), frappe.DoesNotExistError)
		agency_doc = frappe.get_doc("Agency", agency_id)
	else:
		_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)

	agency_doc.billing_status = "Active"
	_mark_trial_converted(agency_doc)
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	_create_agency_audit_comment(
		agency_doc.name,
		_("Agency billing activated by {0}.").format(frappe.session.user),
	)

	return {
		"context": get_agency_access_context(agency_id=agency_doc.name),
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist(methods=["POST"])
def update_agency_team_member(agent_name: str, data: str | None = None) -> dict[str, Any]:
	if not frappe.db.exists("Agent", agent_name):
		frappe.throw(_("Agent not found."), frappe.DoesNotExistError)

	member = frappe.get_doc("Agent", agent_name)
	if not member.agency:
		frappe.throw(_("Agent is not linked to an agency."))

	context, agency_doc = _require_agency_access(agency_id=member.agency, require_team=True)
	if member.agency != agency_doc.name:
		frappe.throw(_("You do not have access to this team member."), frappe.PermissionError)

	payload = _parse_payload(data)
	for fieldname in TEAM_EDITABLE_FIELDS:
		if fieldname in payload:
			member.set(fieldname, payload.get(fieldname))

	member.flags.ignore_permissions = True
	member.save()

	utils.ensure_agency_member_crm_roles(member.user, member.agency_role)

	del context
	return _serialize_team_member(member.as_dict())


def _list_agent_levels(*, active_only: int = 0) -> list[dict[str, Any]]:
	filters = {"active": 1} if cint(active_only) else {}
	rows = frappe.get_all(
		"Agent Level",
		filters=filters,
		fields=["name", "level_name", "daily_rate", "currency", "active", "sort_order", "description"],
		order_by="sort_order asc, level_name asc",
	)
	return [_serialize_agent_level(row) for row in rows]


@frappe.whitelist()
def list_agent_levels(active_only: int = 0) -> list[dict[str, Any]]:
	if not cint(active_only):
		_require_internal_manager()
	return _list_agent_levels(active_only=active_only)


@frappe.whitelist(methods=["POST"])
def save_agent_level(name: str | None = None, data: str | None = None) -> dict[str, Any]:
	_require_internal_manager()
	_require_billing_enabled()
	payload = _parse_payload(data)

	doc = frappe.get_doc("Agent Level", name) if name else frappe.new_doc("Agent Level")
	for fieldname in ["level_name", "daily_rate", "currency", "active", "sort_order", "description"]:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	if flt(doc.daily_rate or 0) < 0:
		frappe.throw(_("Daily rate cannot be negative."))

	doc.flags.ignore_permissions = True
	(doc.insert if doc.is_new() else doc.save)()
	return _serialize_agent_level(doc.as_dict())


@frappe.whitelist(methods=["DELETE"])
def delete_agent_level(name: str) -> dict[str, Any]:
	_require_internal_manager()
	_require_billing_enabled()
	if frappe.db.exists("Agent", {"agent_level": name}):
		frappe.throw(_("This level is still assigned to one or more agents."))
	frappe.delete_doc("Agent Level", name, ignore_permissions=True)
	return {"ok": True}


def _list_billing_addons(*, active_only: int = 0) -> list[dict[str, Any]]:
	filters = {"active": 1} if cint(active_only) else {}
	rows = frappe.get_all(
		"Billing Addon",
		filters=filters,
		fields=["name", "addon_name", "pricing_model", "rate", "currency", "unit_label", "active", "sort_order", "description"],
		order_by="sort_order asc, addon_name asc",
	)
	return [_serialize_billing_addon(row) for row in rows]


@frappe.whitelist()
def list_billing_addons(active_only: int = 0) -> list[dict[str, Any]]:
	if not cint(active_only):
		_require_internal_manager()
	return _list_billing_addons(active_only=active_only)


@frappe.whitelist(methods=["POST"])
def save_billing_addon(name: str | None = None, data: str | None = None) -> dict[str, Any]:
	_require_internal_manager()
	_require_billing_enabled()
	payload = _parse_payload(data)

	doc = frappe.get_doc("Billing Addon", name) if name else frappe.new_doc("Billing Addon")
	for fieldname in [
		"addon_name",
		"pricing_model",
		"rate",
		"currency",
		"unit_label",
		"active",
		"sort_order",
		"description",
	]:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	if flt(doc.rate or 0) < 0:
		frappe.throw(_("Addon rate cannot be negative."))

	doc.flags.ignore_permissions = True
	(doc.insert if doc.is_new() else doc.save)()
	return _serialize_billing_addon(doc.as_dict())


@frappe.whitelist(methods=["DELETE"])
def delete_billing_addon(name: str) -> dict[str, Any]:
	_require_internal_manager()
	_require_billing_enabled()
	for agency in frappe.get_all("Agency", fields=["name"]):
		agency_doc = frappe.get_doc("Agency", agency.name)
		if any(row.addon == name for row in agency_doc.billing_addons or []):
			frappe.throw(_("This addon is still enabled for one or more agencies."))
	frappe.delete_doc("Billing Addon", name, ignore_permissions=True)
	return {"ok": True}


def _ensure_accrual(values: dict[str, Any]):
	key = values.get("accrual_key")
	if key and frappe.db.exists("Agency Billing Accrual", {"accrual_key": key}):
		return None

	doc = frappe.get_doc({"doctype": "Agency Billing Accrual", **values})
	doc.flags.ignore_permissions = True
	try:
		doc.insert()
	except frappe.DuplicateEntryError:
		return None
	return doc


def run_daily_agency_billing(run_date: str | None = None) -> dict[str, Any]:
	if not _is_billing_enabled():
		return {"date": str(getdate(run_date or today())), "created": 0, "skipped": "billing_disabled"}

	target_date = getdate(run_date or today())
	period_start = str(get_first_day(target_date))
	period_end = str(get_last_day(target_date))
	created = 0

	agents = frappe.get_all(
		"Agent",
		filters={"agency": ["is", "set"], "status": "Verified", "billable": 1, "agent_level": ["is", "set"]},
		fields=[
			"name",
			"agency",
			"agent_level",
			"billing_start_date",
			"billing_end_date",
		],
	)

	for row in agents:
		if row.get("billing_start_date") and getdate(row["billing_start_date"]) > target_date:
			continue
		if row.get("billing_end_date") and getdate(row["billing_end_date"]) < target_date:
			continue

		agency_doc = frappe.get_doc("Agency", row["agency"])
		if agency_doc.status != "Active":
			continue
		is_trial_waived = _agency_waives_daily_billing_during_trial(agency_doc)

		if not row.get("agent_level") or not frappe.db.exists("Agent Level", row["agent_level"]):
			# Skip misconfigured agents referencing deleted levels; don't break the daily job.
			continue
		level_doc = frappe.get_doc("Agent Level", row["agent_level"])
		if not cint(level_doc.active):
			continue
		original_rate = flt(level_doc.daily_rate or 0)
		if original_rate <= 0:
			# Misconfigured level should not produce accrual rows (even waived).
			continue

		description = f"{level_doc.level_name} daily charge for {row['name']}"
		rate_to_apply = original_rate
		if is_trial_waived:
			description = f"(Trial Waived) {description} — original rate {original_rate}"
			rate_to_apply = 0

		accrual = _ensure_accrual(
			{
				"agency": agency_doc.name,
				"agent": row["name"],
				"posting_date": str(target_date),
				"billing_period_start": period_start,
				"billing_period_end": period_end,
				"entry_type": "Agent Level",
				"agent_level": level_doc.name,
				"quantity": 1,
				"rate": rate_to_apply,
				"currency": level_doc.currency or _get_default_currency(agency_doc),
				"description": description,
				"status": "Open",
				"accrual_key": f"agent_level::{agency_doc.name}::{row['name']}::{target_date}::{level_doc.name}",
			}
		)
		if accrual:
			created += 1

	for agency in frappe.get_all("Agency", filters={"status": "Active"}, fields=["name"]):
		agency_doc = frappe.get_doc("Agency", agency.name)
		is_trial_waived = _agency_waives_daily_billing_during_trial(agency_doc)
		for addon_row in agency_doc.billing_addons or []:
			if not addon_row.addon or not cint(addon_row.enabled):
				continue
			if not frappe.db.exists("Billing Addon", addon_row.addon):
				# Skip stale addon links; don't break the daily job.
				continue
			addon_doc = frappe.get_doc("Billing Addon", addon_row.addon)
			if not cint(addon_doc.active):
				continue
			if addon_doc.pricing_model == "Usage Based":
				continue
			if _get_addon_charge_timing() == "upfront_immediate":
				continue

			original_rate = flt(addon_row.custom_rate) if addon_row.custom_rate else flt(addon_doc.rate)
			if original_rate <= 0:
				original_rate = flt(addon_doc.rate)
			if original_rate <= 0:
				continue
			accrual_key = None
			posting_date = str(target_date)
			quantity = flt(addon_row.quantity or 1)

			if addon_doc.pricing_model == "Daily Fixed":
				accrual_key = f"addon_daily::{agency_doc.name}::{addon_doc.name}::{target_date}"
			else:
				accrual_key = f"addon_monthly::{agency_doc.name}::{addon_doc.name}::{period_start}"
				posting_date = period_start

			description = f"{addon_doc.addon_name} ({addon_doc.pricing_model})"
			rate_to_apply = original_rate
			if is_trial_waived:
				description = f"(Trial Waived) {description} — original rate {original_rate}"
				rate_to_apply = 0

			accrual = _ensure_accrual(
				{
					"agency": agency_doc.name,
					"posting_date": posting_date,
					"billing_period_start": period_start,
					"billing_period_end": period_end,
					"entry_type": "Addon",
					"addon": addon_doc.name,
					"quantity": quantity,
					"rate": rate_to_apply,
					"currency": addon_doc.currency or agency_doc.billing_currency or _get_default_currency(agency_doc),
					"description": description,
					"status": "Open",
					"accrual_key": accrual_key,
				}
			)
			if accrual:
				created += 1

	return {"date": str(target_date), "created": created}


def run_daily_agency_trial_maintenance(run_date: str | None = None) -> dict[str, Any]:
	target_date = getdate(run_date or today())
	trial_config = _get_trial_config()
	grace_days = trial_config["trial_grace_days"]

	updated = {"active": 0, "grace": 0, "expired": 0}
	rows = frappe.get_all(
		"Agency",
		filters={"trial_status": ["in", ["Active", "Grace"]]},
		fields=["name", "trial_status", "trial_end_date", "trial_grace_end_date", "billing_status"],
	)

	for row in rows:
		agency_doc = frappe.get_doc("Agency", row["name"])
		if not agency_doc.trial_end_date:
			continue

		end_date = getdate(agency_doc.trial_end_date)
		changed = False
		if target_date <= end_date:
			if agency_doc.trial_status != "Active":
				agency_doc.trial_status = "Active"
				agency_doc.is_on_trial = 1
				changed = True
				updated["active"] += 1
		else:
			if grace_days > 0:
				grace_end = (
					getdate(agency_doc.trial_grace_end_date)
					if agency_doc.trial_grace_end_date
					else getdate(add_days(end_date, grace_days))
				)
				if not agency_doc.trial_grace_end_date:
					agency_doc.trial_grace_end_date = str(grace_end)
					changed = True
				if target_date <= grace_end:
					if agency_doc.trial_status != "Grace":
						agency_doc.trial_status = "Grace"
						agency_doc.is_on_trial = 1
						changed = True
						updated["grace"] += 1
				else:
					if agency_doc.trial_status != "Expired":
						agency_doc.trial_status = "Expired"
						agency_doc.is_on_trial = 0
						if agency_doc.billing_status != "Active":
							agency_doc.billing_status = "Past Due"
						changed = True
						updated["expired"] += 1
			else:
				if agency_doc.trial_status != "Expired":
					agency_doc.trial_status = "Expired"
					agency_doc.is_on_trial = 0
					if agency_doc.billing_status != "Active":
						agency_doc.billing_status = "Past Due"
					changed = True
					updated["expired"] += 1

		if changed:
			agency_doc.flags.ignore_permissions = True
			agency_doc.save()

	return {"date": str(target_date), **updated}


def _build_invoice_items(accruals: list[dict[str, Any]]) -> list[dict[str, Any]]:
	grouped: dict[tuple[str, str, str, str, float], dict[str, Any]] = {}
	for row in accruals:
		key = (
			row.get("entry_type") or "",
			row.get("description") or "",
			row.get("agent") or "",
			row.get("addon") or "",
			flt(row.get("rate") or 0),
		)
		entry = grouped.setdefault(
			key,
			{
				"entry_type": row.get("entry_type"),
				"description": row.get("description"),
				"agent": row.get("agent"),
				"agent_level": row.get("agent_level"),
				"addon": row.get("addon"),
				"quantity": 0,
				"rate": flt(row.get("rate") or 0),
				"amount": 0,
				"source_accrual": row.get("name"),
			},
		)
		entry["quantity"] += flt(row.get("quantity") or 0)
		entry["amount"] += flt(row.get("amount") or 0)
		if entry["source_accrual"] != row.get("name"):
			entry["source_accrual"] = None
	items = list(grouped.values())
	# Be resilient to stale links: invoice creation should not fail if an accrual
	# references a deleted Agent/Agent Level/Add-on.
	for item in items:
		if item.get("agent") and not frappe.db.exists("Agent", item.get("agent")):
			item["agent"] = None
		if item.get("agent_level") and not frappe.db.exists("Agent Level", item.get("agent_level")):
			item["agent_level"] = None
		if item.get("addon") and not frappe.db.exists("Billing Addon", item.get("addon")):
			item["addon"] = None
	return items


def _to_minor_units(amount: float) -> int:
	return int(round(flt(amount) * 100))


def _to_minor_units_for_currency(amount: float, currency: str | None) -> int:
	code = (currency or "").lower()
	multiplier = 1 if code in ZERO_DECIMAL_CURRENCIES else 100
	return int(round(flt(amount) * multiplier))


def _validate_redirect_url(url: str | None, fallback: str) -> str:
	if not url:
		return fallback

	url = url.strip()
	if not url:
		return fallback

	site_url = get_url()
	site_parts = urlparse(site_url)

	if url.startswith("/"):
		return get_url(url)

	parts = urlparse(url)
	if parts.scheme not in {"http", "https"} or not parts.netloc:
		frappe.throw(_("Invalid redirect URL."))
	if parts.netloc != site_parts.netloc:
		frappe.throw(_("Redirect URL host must match this site."))
	return url


def _get_stripe_sdk():
	settings = _get_billing_settings()
	if not settings:
		frappe.throw(_("Agency Billing Settings is not configured."))
	secret_key = settings.get_password("stripe_secret_key", raise_exception=False)
	if not secret_key:
		frappe.throw(_("Stripe secret key is not configured."))

	try:
		import stripe  # type: ignore
	except ImportError as exc:
		frappe.throw(_("Stripe SDK is not installed in this bench."), exc=exc)

	stripe.api_key = secret_key
	stripe.default_http_client = stripe.http_client.RequestsClient()
	return stripe, settings


def _ensure_stripe_customer(agency_doc):
	if agency_doc.stripe_customer_id:
		return agency_doc.stripe_customer_id

	stripe, _settings = _get_stripe_sdk()
	customer = stripe.Customer.create(
		name=agency_doc.agency_name,
		email=agency_doc.billing_email or agency_doc.email,
		metadata={"agency": agency_doc.name},
	)

	agency_doc.stripe_customer_id = customer.id
	agency_doc.billing_status = "Active"
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()
	return customer.id


def _has_billing_setup(agency_doc) -> bool:
	return bool(getattr(agency_doc, "stripe_default_payment_method_id", None))


def _get_or_create_agency_payment_method(agency_name: str, stripe_payment_method_id: str):
	existing_name = frappe.db.get_value(
		"Agency Payment Method",
		{"stripe_payment_method_id": stripe_payment_method_id},
		"name",
	)
	if existing_name:
		return frappe.get_doc("Agency Payment Method", existing_name), False

	doc = frappe.get_doc(
		{
			"doctype": "Agency Payment Method",
			"agency": agency_name,
			"stripe_payment_method_id": stripe_payment_method_id,
			"status": "Active",
		}
	)
	return doc, True


def _set_local_default_payment_method(agency_name: str, stripe_payment_method_id: str | None):
	frappe.db.sql(
		"""
		update `tabAgency Payment Method`
		set is_default = 0
		where agency = %s
		""",
		(agency_name,),
	)
	if stripe_payment_method_id:
		pm_name = frappe.db.get_value(
			"Agency Payment Method",
			{"agency": agency_name, "stripe_payment_method_id": stripe_payment_method_id},
			"name",
		)
		if pm_name:
			frappe.db.set_value("Agency Payment Method", pm_name, "is_default", 1, update_modified=False)
			frappe.db.set_value("Agency Payment Method", pm_name, "status", "Active", update_modified=False)


def _sync_agency_default_payment_method(agency_doc, stripe_payment_method_id: str | None):
	agency_doc.stripe_default_payment_method_id = stripe_payment_method_id
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()
	_set_local_default_payment_method(agency_doc.name, stripe_payment_method_id)


def _upsert_agency_payment_method_from_stripe(
	*,
	agency_doc,
	stripe_customer_id: str | None,
	stripe_payment_method,
	mark_default: bool = False,
):
	if not stripe_payment_method:
		return None

	pm_id = stripe_payment_method.get("id") if isinstance(stripe_payment_method, dict) else getattr(stripe_payment_method, "id", None)
	if not pm_id:
		return None

	doc, is_new = _get_or_create_agency_payment_method(agency_doc.name, pm_id)
	card = (
		(stripe_payment_method.get("card") if isinstance(stripe_payment_method, dict) else getattr(stripe_payment_method, "card", None))
		or {}
	)
	pm_type = stripe_payment_method.get("type") if isinstance(stripe_payment_method, dict) else getattr(stripe_payment_method, "type", None)
	card_brand = card.get("brand") if isinstance(card, dict) else getattr(card, "brand", None)
	card_last4 = card.get("last4") if isinstance(card, dict) else getattr(card, "last4", None)
	card_exp_month = card.get("exp_month") if isinstance(card, dict) else getattr(card, "exp_month", None)
	card_exp_year = card.get("exp_year") if isinstance(card, dict) else getattr(card, "exp_year", None)
	doc.agency = agency_doc.name
	doc.stripe_customer_id = stripe_customer_id or agency_doc.stripe_customer_id
	doc.stripe_payment_method_id = pm_id
	doc.type = pm_type or "card"
	doc.brand = card_brand
	doc.last4 = card_last4
	doc.exp_month = cint(card_exp_month or 0)
	doc.exp_year = cint(card_exp_year or 0)
	doc.status = "Active"
	doc.detached_on = None
	doc.flags.ignore_permissions = True
	if is_new:
		doc.insert()
	else:
		doc.save()

	if mark_default:
		_sync_agency_default_payment_method(agency_doc, pm_id)

	return doc


def _set_stripe_customer_default_payment_method(customer_id: str, stripe_payment_method_id: str | None):
	if not customer_id:
		return
	stripe, _settings = _get_stripe_sdk()
	stripe.Customer.modify(
		customer_id,
		invoice_settings={"default_payment_method": stripe_payment_method_id or ""},
	)


def _attach_and_sync_payment_method(
	*,
	agency_doc,
	customer_id: str | None,
	stripe_payment_method_id: str,
	make_default: bool = True,
):
	stripe, _settings = _get_stripe_sdk()
	effective_customer = customer_id or agency_doc.stripe_customer_id or _ensure_stripe_customer(agency_doc)

	try:
		stripe.PaymentMethod.attach(stripe_payment_method_id, customer=effective_customer)
	except Exception:
		# Ignore "already attached" style errors; retrieval below still synchronizes local state.
		pass

	payment_method = stripe.PaymentMethod.retrieve(stripe_payment_method_id)
	_upsert_agency_payment_method_from_stripe(
		agency_doc=agency_doc,
		stripe_customer_id=effective_customer,
		stripe_payment_method=payment_method,
		mark_default=make_default,
	)

	if make_default:
		_set_stripe_customer_default_payment_method(effective_customer, stripe_payment_method_id)
		_sync_agency_default_payment_method(agency_doc, stripe_payment_method_id)


def _find_agency_by_customer(customer_id: str | None) -> str | None:
	if not customer_id:
		return None
	return frappe.db.get_value("Agency", {"stripe_customer_id": customer_id}, "name")


def _mark_payment_method_detached(agency_name: str, stripe_payment_method_id: str):
	pm_name = frappe.db.get_value(
		"Agency Payment Method",
		{"agency": agency_name, "stripe_payment_method_id": stripe_payment_method_id},
		"name",
	)
	if not pm_name:
		return
	pm_doc = frappe.get_doc("Agency Payment Method", pm_name)
	pm_doc.status = "Detached"
	pm_doc.is_default = 0
	pm_doc.detached_on = now_datetime()
	pm_doc.flags.ignore_permissions = True
	pm_doc.save()


def _start_agency_trial(agency_doc):
	trial_config = _get_trial_config()
	if not trial_config["enabled"]:
		return
	if trial_config["requires_payment_method"] and not _has_billing_setup(agency_doc):
		frappe.throw(_("A payment method is required before starting the trial."))

	start_date = getdate(today())
	end_date = add_days(start_date, trial_config["trial_days"] - 1)
	agency_doc.is_on_trial = 1
	agency_doc.trial_status = "Active"
	agency_doc.trial_start_date = str(start_date)
	agency_doc.trial_end_date = str(end_date)
	agency_doc.trial_grace_end_date = None


def _mark_trial_converted(agency_doc):
	if hasattr(agency_doc, "is_on_trial"):
		agency_doc.is_on_trial = 0
	if hasattr(agency_doc, "trial_status"):
		agency_doc.trial_status = "Converted"


def _create_agency_audit_comment(agency_name: str, content: str):
	try:
		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Agency",
				"reference_name": agency_name,
				"content": content,
			}
		)
		comment.flags.ignore_permissions = True
		comment.insert()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Agency billing audit comment failed")


def _sync_invoice_to_stripe(invoice_doc):
	if invoice_doc.stripe_invoice_id:
		return invoice_doc

	stripe, settings = _get_stripe_sdk()
	agency_doc = frappe.get_doc("Agency", invoice_doc.agency)
	customer_id = _ensure_stripe_customer(agency_doc)
	currency = (invoice_doc.currency or _get_default_currency(agency_doc)).lower()

	# Reuse existing Stripe invoice for this CRM invoice when a retry occurs.
	try:
		existing_invoices = stripe.Invoice.list(customer=customer_id, limit=20)
	except Exception:
		existing_invoices = []
	existing_invoice = next(
		(
			inv
			for inv in (getattr(existing_invoices, "data", []) or [])
			if (getattr(inv, "metadata", {}) or {}).get("crm_invoice") == invoice_doc.name
		),
		None,
	)
	if existing_invoice:
		stripe_invoice = existing_invoice
		if getattr(stripe_invoice, "status", None) == "draft":
			stripe_invoice = stripe.Invoice.finalize_invoice(stripe_invoice.id)
		invoice_doc.stripe_customer_id = customer_id
		invoice_doc.stripe_invoice_id = stripe_invoice.id
		invoice_doc.stripe_status = stripe_invoice.status
		invoice_doc.stripe_hosted_invoice_url = getattr(stripe_invoice, "hosted_invoice_url", None)
		invoice_doc.status = "Open"
		invoice_doc.flags.ignore_permissions = True
		invoice_doc.save()
		return invoice_doc

	for item in invoice_doc.items or []:
		stripe.InvoiceItem.create(
			customer=customer_id,
			currency=currency,
			amount=_to_minor_units_for_currency(item.amount, currency),
			description=item.description,
			metadata={"crm_invoice": invoice_doc.name, "agency": agency_doc.name},
			idempotency_key=f"crm_invoice_item::{invoice_doc.name}::{item.name or item.idx or item.description}",
		)

	invoice_kwargs: dict[str, Any] = {
		"customer": customer_id,
		"collection_method": settings.stripe_collection_method or "send_invoice",
		"auto_advance": True,
		"metadata": {"crm_invoice": invoice_doc.name, "agency": agency_doc.name},
	}
	if invoice_kwargs["collection_method"] == "charge_automatically" and agency_doc.stripe_default_payment_method_id:
		invoice_kwargs["default_payment_method"] = agency_doc.stripe_default_payment_method_id
	if invoice_kwargs["collection_method"] == "send_invoice":
		invoice_kwargs["days_until_due"] = cint(settings.invoice_due_days or 0)

	stripe_invoice = stripe.Invoice.create(
		**invoice_kwargs,
		idempotency_key=f"crm_invoice::{invoice_doc.name}",
	)
	if getattr(stripe_invoice, "status", None) == "draft":
		stripe_invoice = stripe.Invoice.finalize_invoice(stripe_invoice.id)

	invoice_doc.stripe_customer_id = customer_id
	invoice_doc.stripe_invoice_id = stripe_invoice.id
	invoice_doc.stripe_status = stripe_invoice.status
	invoice_doc.stripe_hosted_invoice_url = getattr(stripe_invoice, "hosted_invoice_url", None)
	invoice_doc.status = "Open"
	invoice_doc.flags.ignore_permissions = True
	invoice_doc.save()
	return invoice_doc


def _close_billing_period(
	period_start: str | None = None,
	period_end: str | None = None,
	agency_id: str | None = None,
	*,
	sync_to_stripe: bool = True,
) -> list[dict[str, Any]]:
	if not _is_billing_enabled():
		return []

	if period_start and period_end:
		start_date = str(getdate(period_start))
		end_date = str(getdate(period_end))
	else:
		previous_month = add_months(getdate(today()), -1)
		start_date = str(get_first_day(previous_month))
		end_date = str(get_last_day(previous_month))

	run_daily_agency_billing(end_date)

	filters = {"status": "Open", "billing_period_start": start_date, "billing_period_end": end_date}
	if agency_id:
		filters["agency"] = agency_id

	agencies = frappe.get_all("Agency Billing Accrual", filters=filters, fields=["agency"], group_by="agency")
	created_invoices = []

	for row in agencies:
		agency_name = row.get("agency")
		if not agency_name:
			continue

		existing = frappe.get_all(
			"Agency Billing Invoice",
			filters={"agency": agency_name, "billing_period_start": start_date, "billing_period_end": end_date},
			fields=["name"],
			limit=1,
		)
		if existing:
			existing_doc = frappe.get_doc("Agency Billing Invoice", existing[0]["name"])
			# Backfill trial flag for invoices created before the `trial_waived` field existed.
			try:
				if not cint(getattr(existing_doc, "trial_waived", 0)) and any(
					(str(r.description or "")).startswith("(Trial Waived)") for r in (existing_doc.items or [])
				):
					frappe.db.set_value(
						"Agency Billing Invoice",
						existing_doc.name,
						"trial_waived",
						1,
						update_modified=False,
					)
					existing_doc.trial_waived = 1
			except Exception:
				pass
			created_invoices.append(_serialize_invoice(existing_doc))
			continue

		accruals = frappe.get_all(
			"Agency Billing Accrual",
			filters={**filters, "agency": agency_name},
			fields=[
				"name",
				"entry_type",
				"description",
				"agent",
				"agent_level",
				"addon",
				"quantity",
				"rate",
				"amount",
				"currency",
			],
			order_by="posting_date asc, creation asc",
		)
		if not accruals:
			continue

		agency_doc = frappe.get_doc("Agency", agency_name)
		is_trial_waived_invoice = _agency_waives_daily_billing_during_trial(agency_doc) and any(
			(str(r.get("description") or "")).startswith("(Trial Waived)") for r in accruals
		)
		invoice_doc = frappe.get_doc(
			{
				"doctype": "Agency Billing Invoice",
				"agency": agency_name,
				"status": "Draft",
				"trial_waived": 1 if is_trial_waived_invoice else 0,
				"currency": accruals[0]["currency"] or _get_default_currency(agency_doc),
				"invoice_date": end_date,
				"due_date": add_days(end_date, cint((_get_billing_settings() or frappe._dict(invoice_due_days=7)).invoice_due_days or 7)),
				"billing_period_start": start_date,
				"billing_period_end": end_date,
				"items": _build_invoice_items(accruals),
			}
		)
		invoice_doc.flags.ignore_permissions = True
		invoice_doc.insert()

		for accrual in accruals:
			frappe.db.set_value(
				"Agency Billing Accrual",
				accrual["name"],
				{"invoice": invoice_doc.name, "status": "Invoiced"},
				update_modified=False,
			)

		if sync_to_stripe and _stripe_enabled():
			try:
				invoice_doc = _sync_invoice_to_stripe(invoice_doc)
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Agency billing Stripe sync failed")
				invoice_doc.reload()
				invoice_doc.status = "Failed"
				invoice_doc.error_message = "Stripe invoice creation failed. Check error logs."
				invoice_doc.flags.ignore_permissions = True
				invoice_doc.save()

		created_invoices.append(_serialize_invoice(invoice_doc))

	return created_invoices


def close_previous_month_agency_billing():
	# Monthly job: create invoices from accruals but do not sync/charge via Stripe.
	return _close_billing_period(sync_to_stripe=False)


@frappe.whitelist(methods=["POST"])
def close_agency_billing_period(
	period_start: str | None = None,
	period_end: str | None = None,
	agency_id: str | None = None,
) -> list[dict[str, Any]]:
	_require_internal_manager()
	_require_billing_enabled()
	return _close_billing_period(period_start=period_start, period_end=period_end, agency_id=agency_id)


@frappe.whitelist(methods=["POST"])
def pay_agency_invoice(invoice_name: str) -> dict[str, Any]:
	_require_billing_enabled()
	if not frappe.db.exists("Agency Billing Invoice", invoice_name):
		frappe.throw(_("Invoice not found."), frappe.DoesNotExistError)

	invoice_doc = frappe.get_doc("Agency Billing Invoice", invoice_name)
	_require_agency_access(agency_id=invoice_doc.agency, require_billing=True)

	if invoice_doc.stripe_hosted_invoice_url:
		return _serialize_invoice(invoice_doc)

	if not _stripe_enabled():
		frappe.throw(_("Stripe is not configured for billing."))

	if not invoice_doc.stripe_invoice_id:
		invoice_doc = _sync_invoice_to_stripe(invoice_doc)

	return _serialize_invoice(invoice_doc)


@frappe.whitelist(methods=["POST"])
def create_billing_setup_session(
	agency_id: str | None = None,
	success_url: str | None = None,
	cancel_url: str | None = None,
) -> dict[str, Any]:
	_require_billing_enabled()
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	stripe, _settings = _get_stripe_sdk()
	customer_id = _ensure_stripe_customer(agency_doc)

	default_success = f"{get_url('/crm/agency-onboarding')}?billing=success"
	default_cancel = f"{get_url('/crm/agency-onboarding')}?billing=cancel"
	success_url = _validate_redirect_url(success_url, default_success)
	cancel_url = _validate_redirect_url(cancel_url, default_cancel)
	currency = (agency_doc.billing_currency or _get_default_currency(agency_doc) or "USD").lower()

	session = stripe.checkout.Session.create(
		mode="setup",
		customer=customer_id,
		currency=currency,
		success_url=success_url,
		cancel_url=cancel_url,
		metadata={"agency": agency_doc.name, "intent": "billing_setup"},
	)

	agency_doc.onboarding_status = "In Progress"
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()

	return {
		"url": session.url,
		"customer_id": customer_id,
		"payment_mode": _get_payment_mode(),
		"trial_config": _get_trial_config(),
	}


@frappe.whitelist(methods=["POST"])
def create_add_card_setup_session(
	agency_id: str | None = None,
	success_url: str | None = None,
	cancel_url: str | None = None,
) -> dict[str, Any]:
	_require_billing_enabled()
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	stripe, _settings = _get_stripe_sdk()
	customer_id = _ensure_stripe_customer(agency_doc)

	default_success = f"{get_url('/crm/settings?section=billing')}?billing=card_added"
	default_cancel = f"{get_url('/crm/settings?section=billing')}?billing=card_cancel"
	success_url = _validate_redirect_url(success_url, default_success)
	cancel_url = _validate_redirect_url(cancel_url, default_cancel)
	currency = (agency_doc.billing_currency or _get_default_currency(agency_doc) or "USD").lower()

	session = stripe.checkout.Session.create(
		mode="setup",
		customer=customer_id,
		currency=currency,
		success_url=success_url,
		cancel_url=cancel_url,
		metadata={"agency": agency_doc.name, "intent": "add_card"},
	)
	return {"url": session.url, "customer_id": customer_id}


@frappe.whitelist(methods=["POST"])
def create_stripe_setup_intent(
	agency_id: str | None = None,
	intent: str | None = None,
) -> dict[str, Any]:
	"""Create a SetupIntent for Stripe Elements (in-app card capture). Replaces hosted Checkout for add/setup card."""
	_require_billing_enabled()
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	if not _stripe_enabled():
		frappe.throw(_("Stripe is not configured for billing."))
	publishable = _get_stripe_publishable_key()
	if not publishable:
		frappe.throw(_("Stripe publishable key is not configured in Agency Billing Settings."))
	stripe, _settings = _get_stripe_sdk()
	customer_id = _ensure_stripe_customer(agency_doc)
	intent_kind = (intent or "billing_setup").strip()
	if intent_kind not in {"billing_setup", "add_card"}:
		frappe.throw(_("Invalid intent."))

	si = stripe.SetupIntent.create(
		customer=customer_id,
		payment_method_types=["card"],
		usage="off_session",
		metadata={"agency": agency_doc.name, "intent": intent_kind},
	)

	if intent_kind == "billing_setup":
		agency_doc.onboarding_status = "In Progress"
		agency_doc.flags.ignore_permissions = True
		agency_doc.save()

	return {
		"client_secret": si.client_secret,
		"setup_intent_id": si.id,
		"publishable_key": publishable,
	}


@frappe.whitelist(methods=["POST"])
def complete_stripe_setup_intent(
	setup_intent_id: str | None = None,
	agency_id: str | None = None,
) -> dict[str, Any]:
	"""After Elements confirms the SetupIntent, attach the payment method and sync Agency Payment Method."""
	_require_billing_enabled()
	if not setup_intent_id:
		frappe.throw(_("Setup intent ID is required."))
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	if not _stripe_enabled():
		frappe.throw(_("Stripe is not configured for billing."))
	stripe, _settings = _get_stripe_sdk()
	si = stripe.SetupIntent.retrieve(setup_intent_id, expand=["payment_method"])
	meta = getattr(si, "metadata", None) or {}
	if not isinstance(meta, dict):
		meta = dict(meta) if meta else {}
	if meta.get("agency") != agency_doc.name:
		frappe.throw(_("Invalid or expired setup session."), frappe.PermissionError)
	if getattr(si, "status", None) != "succeeded":
		frappe.throw(_("Card verification did not complete. Please try again."))
	pm_ref = getattr(si, "payment_method", None)
	pm_id = pm_ref.get("id") if isinstance(pm_ref, dict) else pm_ref
	if not pm_id:
		frappe.throw(_("No payment method was returned from Stripe."))
	intent_kind = (meta.get("intent") or "billing_setup").strip()
	make_default = intent_kind != "add_card" or not agency_doc.stripe_default_payment_method_id
	agency_doc = frappe.get_doc("Agency", agency_doc.name)
	_attach_and_sync_payment_method(
		agency_doc=agency_doc,
		customer_id=agency_doc.stripe_customer_id,
		stripe_payment_method_id=pm_id,
		make_default=make_default,
	)
	agency_doc = frappe.get_doc("Agency", agency_doc.name)
	agency_doc.billing_status = "Active"
	agency_doc.flags.ignore_permissions = True
	agency_doc.save()
	return {
		"ok": True,
		"saved_payment_methods": _list_saved_payment_methods_internal(agency_doc.name),
		"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		"agency": _serialize_agency(agency_doc),
	}


@frappe.whitelist()
def list_all_agency_billing_invoices(
	status: str | None = None,
	agency: str | None = None,
	limit: int = 50,
	start: int = 0,
) -> list[dict[str, Any]]:
	"""All agencies' invoices — CRM managers only (Settings overview)."""
	_require_internal_manager()
	if not _is_billing_enabled():
		return []
	filters: dict[str, Any] = {}
	if status:
		filters["status"] = status
	if agency:
		filters["agency"] = agency
	lim = max(1, min(cint(limit or 50), 200))
	off = max(0, cint(start or 0))
	rows = frappe.get_all(
		"Agency Billing Invoice",
		filters=filters or None,
		fields=[
			"name",
			"agency",
			"status",
			"currency",
			"invoice_date",
			"due_date",
			"billing_period_start",
			"billing_period_end",
			"subtotal",
			"total",
			"stripe_invoice_id",
			"stripe_status",
			"stripe_hosted_invoice_url",
			"paid_on",
			"error_message",
		],
		order_by="invoice_date desc, creation desc",
		limit_start=off,
		limit_page_length=lim,
	)
	agency_ids = {r["agency"] for r in rows if r.get("agency")}
	agency_labels: dict[str, str] = {}
	for aid in agency_ids:
		if aid:
			agency_labels[aid] = frappe.db.get_value("Agency", aid, "agency_name") or aid
	out: list[dict[str, Any]] = []
	for row in rows:
		inv = _serialize_invoice(row, include_items=False)
		inv["agency_display_name"] = agency_labels.get(row.get("agency"), row.get("agency"))
		out.append(inv)
	return out


@frappe.whitelist()
def list_saved_payment_methods(agency_id: str | None = None) -> dict[str, Any]:
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	return {
		"agency": agency_doc.name,
		"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		"saved_payment_methods": _list_saved_payment_methods_internal(agency_doc.name),
	}


@frappe.whitelist(methods=["POST"])
def set_default_payment_method(agency_id: str | None = None, stripe_payment_method_id: str | None = None) -> dict[str, Any]:
	_require_billing_enabled()
	if not stripe_payment_method_id:
		frappe.throw(_("Stripe payment method ID is required."))
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	customer_id = _ensure_stripe_customer(agency_doc)

	pm_name = frappe.db.get_value(
		"Agency Payment Method",
		{"agency": agency_doc.name, "stripe_payment_method_id": stripe_payment_method_id},
		"name",
	)
	if not pm_name:
		frappe.throw(_("Payment method not found for this agency."), frappe.DoesNotExistError)

	pm_doc = frappe.get_doc("Agency Payment Method", pm_name)
	if pm_doc.status == "Detached":
		frappe.throw(_("Detached payment methods cannot be set as default."))

	_set_stripe_customer_default_payment_method(customer_id, stripe_payment_method_id)
	_sync_agency_default_payment_method(agency_doc, stripe_payment_method_id)

	return {
		"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		"saved_payment_methods": _list_saved_payment_methods_internal(agency_doc.name),
	}


@frappe.whitelist(methods=["POST"])
def detach_payment_method(agency_id: str | None = None, stripe_payment_method_id: str | None = None) -> dict[str, Any]:
	_require_billing_enabled()
	if not stripe_payment_method_id:
		frappe.throw(_("Stripe payment method ID is required."))
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	customer_id = _ensure_stripe_customer(agency_doc)

	pm_name = frappe.db.get_value(
		"Agency Payment Method",
		{"agency": agency_doc.name, "stripe_payment_method_id": stripe_payment_method_id},
		"name",
	)
	if not pm_name:
		frappe.throw(_("Payment method not found for this agency."), frappe.DoesNotExistError)

	stripe, _settings = _get_stripe_sdk()
	stripe.PaymentMethod.detach(stripe_payment_method_id)
	_mark_payment_method_detached(agency_doc.name, stripe_payment_method_id)

	if agency_doc.stripe_default_payment_method_id == stripe_payment_method_id:
		remaining_pm = frappe.get_all(
			"Agency Payment Method",
			filters={"agency": agency_doc.name, "status": "Active"},
			fields=["stripe_payment_method_id"],
			order_by="modified desc",
			limit=1,
		)
		next_default = remaining_pm[0]["stripe_payment_method_id"] if remaining_pm else None
		_set_stripe_customer_default_payment_method(customer_id, next_default)
		_sync_agency_default_payment_method(agency_doc, next_default)

	return {
		"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		"saved_payment_methods": _list_saved_payment_methods_internal(agency_doc.name),
	}


@frappe.whitelist(methods=["POST"])
def sync_stripe_payment_methods_from_customer(agency_id: str | None = None) -> dict[str, Any]:
	"""Pull card payment methods and default PM from Stripe into CRM (avoids waiting on webhooks)."""
	_require_billing_enabled()
	_context, agency_doc = _require_agency_access(agency_id=agency_id, require_billing=True)
	if not _stripe_enabled():
		agency_doc.reload()
		return {
			"ok": True,
			"skipped": "stripe_disabled",
			"has_default": bool(agency_doc.stripe_default_payment_method_id),
			"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
		}

	customer_id = _ensure_stripe_customer(agency_doc)
	stripe, _settings = _get_stripe_sdk()
	customer = stripe.Customer.retrieve(customer_id, expand=["invoice_settings.default_payment_method"])

	pms = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=100)
	for pm in getattr(pms, "data", []) or []:
		_upsert_agency_payment_method_from_stripe(
			agency_doc=frappe.get_doc("Agency", agency_doc.name),
			stripe_customer_id=customer_id,
			stripe_payment_method=pm,
			mark_default=False,
		)

	agency_doc = frappe.get_doc("Agency", agency_doc.name)
	inv_settings = getattr(customer, "invoice_settings", None)
	default_pm_obj = getattr(inv_settings, "default_payment_method", None) if inv_settings else None
	if isinstance(default_pm_obj, str) and default_pm_obj:
		default_pm_obj = stripe.PaymentMethod.retrieve(default_pm_obj)

	if default_pm_obj:
		pm_id = (
			default_pm_obj.get("id")
			if isinstance(default_pm_obj, dict)
			else getattr(default_pm_obj, "id", None)
		)
		if pm_id:
			pm_full = (
				default_pm_obj
				if not isinstance(default_pm_obj, str)
				else stripe.PaymentMethod.retrieve(pm_id)
			)
			_upsert_agency_payment_method_from_stripe(
				agency_doc=agency_doc,
				stripe_customer_id=customer_id,
				stripe_payment_method=pm_full,
				mark_default=True,
			)

	agency_doc.reload()
	return {
		"ok": True,
		"has_default": bool(agency_doc.stripe_default_payment_method_id),
		"default_payment_method_id": agency_doc.stripe_default_payment_method_id,
	}


@frappe.whitelist(methods=["POST"])
def record_addon_usage(
	agency_id: str,
	addon: str,
	quantity: float = 1,
	service_date: str | None = None,
	external_reference: str | None = None,
	description: str | None = None,
) -> dict[str, Any]:
	_require_internal_manager()
	_require_billing_enabled()
	if not frappe.db.exists("Agency", agency_id):
		frappe.throw(_("Agency not found."), frappe.DoesNotExistError)
	if not frappe.db.exists("Billing Addon", addon):
		frappe.throw(_("Billing addon not found."), frappe.DoesNotExistError)

	addon_doc = frappe.get_doc("Billing Addon", addon)
	if addon_doc.pricing_model != "Usage Based":
		frappe.throw(_("Only usage-based addons can be recorded through this API."))
	quantity = flt(quantity or 0)
	if quantity <= 0:
		frappe.throw(_("Usage quantity must be greater than zero."))
	if flt(addon_doc.rate or 0) < 0:
		frappe.throw(_("Billing addon rate cannot be negative."))

	agency_doc = frappe.get_doc("Agency", agency_id)
	posting_date = getdate(service_date or today())
	period_start = str(get_first_day(posting_date))
	period_end = str(get_last_day(posting_date))
	accrual = _ensure_accrual(
		{
			"agency": agency_doc.name,
			"posting_date": str(posting_date),
			"billing_period_start": period_start,
			"billing_period_end": period_end,
			"entry_type": "Addon",
			"addon": addon_doc.name,
			"quantity": quantity,
			"rate": flt(addon_doc.rate),
			"currency": addon_doc.currency or agency_doc.billing_currency or _get_default_currency(agency_doc),
			"description": description or f"{addon_doc.addon_name} usage",
			"status": "Open",
			"external_reference": external_reference,
			"accrual_key": f"addon_usage::{agency_doc.name}::{addon_doc.name}::{posting_date}::{external_reference or frappe.generate_hash(length=8)}",
		}
	)

	return {"created": bool(accrual), "name": accrual.name if accrual else None}


def _mark_invoice_paid(invoice_name: str, stripe_status: str | None = None, payment_intent_id: str | None = None):
	if not frappe.db.exists("Agency Billing Invoice", invoice_name):
		return
	invoice_doc = frappe.get_doc("Agency Billing Invoice", invoice_name)
	invoice_doc.status = "Paid"
	invoice_doc.stripe_status = stripe_status or invoice_doc.stripe_status
	invoice_doc.stripe_payment_intent_id = payment_intent_id or invoice_doc.stripe_payment_intent_id
	invoice_doc.paid_on = now_datetime()
	invoice_doc.flags.ignore_permissions = True
	invoice_doc.save()

	for accrual in frappe.get_all("Agency Billing Accrual", filters={"invoice": invoice_name}, pluck="name"):
		frappe.db.set_value("Agency Billing Accrual", accrual, "status", "Paid", update_modified=False)

	if frappe.db.exists("Agency", invoice_doc.agency):
		agency_doc = frappe.get_doc("Agency", invoice_doc.agency)
		agency_doc.billing_status = "Active"
		_mark_trial_converted(agency_doc)
		agency_doc.flags.ignore_permissions = True
		agency_doc.save()


def _mark_invoice_failed(invoice_name: str, stripe_status: str | None = None):
	if not frappe.db.exists("Agency Billing Invoice", invoice_name):
		return
	invoice_doc = frappe.get_doc("Agency Billing Invoice", invoice_name)
	invoice_doc.status = "Failed"
	invoice_doc.stripe_status = stripe_status or invoice_doc.stripe_status
	invoice_doc.flags.ignore_permissions = True
	invoice_doc.save()

	if frappe.db.exists("Agency", invoice_doc.agency):
		agency_doc = frappe.get_doc("Agency", invoice_doc.agency)
		agency_doc.billing_status = "Past Due"
		agency_doc.flags.ignore_permissions = True
		agency_doc.save()


def _truncate_json(value: Any, max_len: int = 1200) -> str:
	text = frappe.as_json(value) if value is not None else ""
	return text if len(text) <= max_len else f"{text[:max_len]}..."


def _extract_webhook_links(event: dict[str, Any]) -> tuple[dict[str, Any], str | None, str | None, str | None]:
	data_object = event.get("data", {}).get("object", {}) or {}
	metadata = data_object.get("metadata") or {}
	customer_id = data_object.get("customer")
	if isinstance(customer_id, dict):
		customer_id = customer_id.get("id")
	return data_object, metadata.get("crm_invoice"), metadata.get("agency"), customer_id


def _upsert_stripe_webhook_event(event: dict[str, Any], payload_text: str, signature: str | None):
	event_id = (event.get("id") or "").strip()
	if not event_id:
		event_id = f"raw-{hashlib.sha256(payload_text.encode('utf-8')).hexdigest()}"

	event_type = event.get("type")
	data_object, invoice_name, agency_name, customer_id = _extract_webhook_links(event)
	resolved_agency = agency_name or _find_agency_by_customer(customer_id)
	if not resolved_agency and invoice_name and frappe.db.exists("Agency Billing Invoice", invoice_name):
		resolved_agency = frappe.db.get_value("Agency Billing Invoice", invoice_name, "agency")

	existing_name = frappe.db.get_value("Stripe Webhook Event", {"event_id": event_id}, "name")
	if existing_name:
		doc = frappe.get_doc("Stripe Webhook Event", existing_name)
		if doc.status not in {"Processed", "Processing"}:
			doc.received_on = now_datetime()
			doc.signature_header = signature
			doc.event_type = event_type
			doc.crm_invoice = invoice_name
			doc.agency = resolved_agency
			doc.stripe_status = data_object.get("status")
			doc.payment_intent_id = data_object.get("payment_intent")
			doc.metadata_json = _truncate_json(data_object.get("metadata") or {})
			doc.payload_json = payload_text
			doc.flags.ignore_permissions = True
			doc.save()
		return doc, False

	doc = frappe.get_doc(
		{
			"doctype": "Stripe Webhook Event",
			"event_id": event_id,
			"event_type": event_type,
			"status": "Received",
			"received_on": now_datetime(),
			"signature_header": signature,
			"agency": resolved_agency,
			"crm_invoice": invoice_name,
			"stripe_status": data_object.get("status"),
			"payment_intent_id": data_object.get("payment_intent"),
			"metadata_json": _truncate_json(data_object.get("metadata") or {}),
			"payload_json": payload_text,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc, True


def _record_stripe_webhook_event(event: dict[str, Any], invoice_name: str | None, agency_name: str | None, data_object: dict[str, Any]):
	"""Persist Stripe webhook traces as comments for audit/debug."""
	event_id = event.get("id")
	event_type = event.get("type")
	stripe_status = data_object.get("status")
	payment_intent = data_object.get("payment_intent")
	metadata_text = _truncate_json(data_object.get("metadata") or {})

	# If agency is not directly present in metadata, infer from CRM invoice.
	customer_id = data_object.get("customer")
	if isinstance(customer_id, dict):
		customer_id = customer_id.get("id")
	resolved_agency = agency_name or _find_agency_by_customer(customer_id)
	if not resolved_agency and invoice_name and frappe.db.exists("Agency Billing Invoice", invoice_name):
		resolved_agency = frappe.db.get_value("Agency Billing Invoice", invoice_name, "agency")

	comment_text = _(
		"Stripe webhook received. Event: {0} ({1}), Invoice: {2}, Agency: {3}, Stripe status: {4}, Payment Intent: {5}, Metadata: {6}"
	).format(
		event_type or "unknown",
		event_id or "n/a",
		invoice_name or "n/a",
		resolved_agency or agency_name or "n/a",
		stripe_status or "n/a",
		payment_intent or "n/a",
		metadata_text or "{}",
	)

	try:
		if resolved_agency and frappe.db.exists("Agency", resolved_agency):
			_create_agency_audit_comment(resolved_agency, comment_text)
		if invoice_name and frappe.db.exists("Agency Billing Invoice", invoice_name):
			invoice_comment = frappe.get_doc(
				{
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": "Agency Billing Invoice",
					"reference_name": invoice_name,
					"content": comment_text,
				}
			)
			invoice_comment.flags.ignore_permissions = True
			invoice_comment.insert()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Stripe webhook event log write failed")


def process_stripe_webhook_event(webhook_event_name: str):
	"""Queued processor for Stripe webhook events saved in Stripe Webhook Event doctype."""
	if not frappe.db.exists("Stripe Webhook Event", webhook_event_name):
		return {"ok": False, "error": "event_not_found"}

	event_log = frappe.get_doc("Stripe Webhook Event", webhook_event_name)
	if event_log.status == "Processed":
		return {"ok": True, "status": "already_processed"}

	try:
		event_log.status = "Processing"
		event_log.attempt_count = cint(event_log.attempt_count or 0) + 1
		event_log.last_error = None
		event_log.flags.ignore_permissions = True
		event_log.save()

		event = frappe.parse_json(event_log.payload_json or "{}") or {}
		data_object, invoice_name, agency_name, customer_id = _extract_webhook_links(event)
		agency_name = agency_name or _find_agency_by_customer(customer_id)
		event_type = event.get("type")

		_record_stripe_webhook_event(event, invoice_name=invoice_name, agency_name=agency_name, data_object=data_object)

		if event_type in {"invoice.paid", "invoice.payment_succeeded"} and invoice_name:
			_mark_invoice_paid(
				invoice_name,
				stripe_status=data_object.get("status"),
				payment_intent_id=data_object.get("payment_intent"),
			)
			event_log.status = "Processed"
		elif event_type == "invoice.payment_failed" and invoice_name:
			_mark_invoice_failed(invoice_name, stripe_status=data_object.get("status"))
			event_log.status = "Processed"
		elif event_type == "checkout.session.completed" and agency_name and frappe.db.exists("Agency", agency_name):
			agency_doc = frappe.get_doc("Agency", agency_name)
			agency_doc.stripe_customer_id = customer_id or agency_doc.stripe_customer_id
			stripe, _settings = _get_stripe_sdk()
			setup_intent_id = data_object.get("setup_intent")
			intent = (data_object.get("metadata") or {}).get("intent")
			if setup_intent_id:
				setup_intent = stripe.SetupIntent.retrieve(setup_intent_id, expand=["payment_method"])
				payment_method = setup_intent.get("payment_method")
				if isinstance(payment_method, str):
					payment_method = stripe.PaymentMethod.retrieve(payment_method)
				make_default = intent != "add_card" or not agency_doc.stripe_default_payment_method_id
				_upsert_agency_payment_method_from_stripe(
					agency_doc=agency_doc,
					stripe_customer_id=customer_id or agency_doc.stripe_customer_id,
					stripe_payment_method=payment_method,
					mark_default=make_default,
				)
				if make_default and payment_method:
					pm_id = payment_method.get("id") if isinstance(payment_method, dict) else getattr(payment_method, "id", None)
					if pm_id:
						_set_stripe_customer_default_payment_method(agency_doc.stripe_customer_id, pm_id)
			agency_doc.billing_status = "Active"
			agency_doc.flags.ignore_permissions = True
			agency_doc.save()
			event_log.status = "Processed"
		elif event_type == "setup_intent.succeeded" and agency_name and frappe.db.exists("Agency", agency_name):
			agency_doc = frappe.get_doc("Agency", agency_name)
			pm_id = data_object.get("payment_method")
			if pm_id:
				_attach_and_sync_payment_method(
					agency_doc=agency_doc,
					customer_id=customer_id,
					stripe_payment_method_id=pm_id,
					make_default=not bool(agency_doc.stripe_default_payment_method_id),
				)
			event_log.status = "Processed"
		elif event_type == "payment_method.attached" and agency_name and frappe.db.exists("Agency", agency_name):
			agency_doc = frappe.get_doc("Agency", agency_name)
			_upsert_agency_payment_method_from_stripe(
				agency_doc=agency_doc,
				stripe_customer_id=customer_id or agency_doc.stripe_customer_id,
				stripe_payment_method=data_object,
				mark_default=False,
			)
			event_log.status = "Processed"
		elif event_type == "payment_method.detached" and agency_name and frappe.db.exists("Agency", agency_name):
			agency_doc = frappe.get_doc("Agency", agency_name)
			pm_id = data_object.get("id")
			if pm_id:
				_mark_payment_method_detached(agency_doc.name, pm_id)
				if agency_doc.stripe_default_payment_method_id == pm_id:
					_sync_agency_default_payment_method(agency_doc, None)
			event_log.status = "Processed"
		elif event_type == "customer.updated" and agency_name and frappe.db.exists("Agency", agency_name):
			agency_doc = frappe.get_doc("Agency", agency_name)
			default_pm_id = ((data_object.get("invoice_settings") or {}).get("default_payment_method")) or None
			if default_pm_id:
				stripe, _settings = _get_stripe_sdk()
				payment_method = stripe.PaymentMethod.retrieve(default_pm_id)
				_upsert_agency_payment_method_from_stripe(
					agency_doc=agency_doc,
					stripe_customer_id=customer_id or agency_doc.stripe_customer_id,
					stripe_payment_method=payment_method,
					mark_default=True,
				)
			else:
				_sync_agency_default_payment_method(agency_doc, None)
			event_log.status = "Processed"
		else:
			event_log.status = "Ignored"

		event_log.processed_on = now_datetime()
		event_log.stripe_status = data_object.get("status") or event_log.stripe_status
		event_log.payment_intent_id = data_object.get("payment_intent") or event_log.payment_intent_id
		event_log.flags.ignore_permissions = True
		event_log.save()
		return {"ok": True, "status": event_log.status}
	except Exception:
		frappe.db.rollback()
		event_log.reload()
		event_log.status = "Failed"
		event_log.last_error = _truncate_json(frappe.get_traceback(), max_len=2000)
		event_log.flags.ignore_permissions = True
		event_log.save()
		frappe.log_error(frappe.get_traceback(), f"Stripe webhook queue processing failed: {webhook_event_name}")
		return {"ok": False, "status": "Failed"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def stripe_webhook():
	frappe.set_user("Administrator")
	stripe, settings = _get_stripe_sdk()
	payload = frappe.request.get_data()
	signature = frappe.get_request_header("Stripe-Signature")
	webhook_secret = settings.get_password("stripe_webhook_secret", raise_exception=False)

	try:
		if webhook_secret:
			event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=webhook_secret)
		else:
			event = frappe.parse_json(payload.decode("utf-8"))
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Agency billing Stripe webhook rejected")
		frappe.response.http_status_code = 400
		return {"ok": False, "error": "invalid_signature_or_payload"}

	payload_text = payload.decode("utf-8")
	webhook_event, created = _upsert_stripe_webhook_event(event, payload_text=payload_text, signature=signature)

	if not created and webhook_event.status == "Processed":
		return {"ok": True, "queued": False, "duplicate": True, "event_id": webhook_event.event_id}
	if not created and webhook_event.status == "Processing":
		return {"ok": True, "queued": False, "processing": True, "event_id": webhook_event.event_id}

	frappe.enqueue(
		"crm.api.redtra.billing.process_stripe_webhook_event",
		queue="long",
		enqueue_after_commit=True,
		webhook_event_name=webhook_event.name,
	)
	return {"ok": True, "queued": True, "event_id": webhook_event.event_id, "event_log": webhook_event.name}
