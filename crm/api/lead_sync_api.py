"""CRM Lead sync API for external systems (portal, ads, partner integrations)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

# Field names accepted on CRM Lead (besides `name` for update)
ALLOWED_LEAD_FIELDS = frozenset(
	{
		"first_name",
		"last_name",
		"email",
		"mobile_no",
		"phone",
		"job_title",
		"status",
		"source",
		"agency",
		"agent_id",
		"territory",
		"website",
		"no_of_employees",
		"annual_revenue",
	}
)

REQUIRED_FOR_INSERT = frozenset({"first_name", "email"})


def _property_fieldname() -> str:
	if not frappe.get_meta("CRM Lead").has_field("custom_property"):
		frappe.throw(
			_(
				"CRM Lead is missing the Property link field `custom_property`. "
				"Run `bench migrate` after updating the CRM app."
			),
			frappe.ValidationError,
		)
	return "custom_property"


def _parse_lead_input(lead) -> dict[str, Any]:
	if lead is None:
		return {}
	if isinstance(lead, str):
		lead = lead.strip()
		if not lead:
			return {}
		return frappe.parse_json(lead) or {}
	if isinstance(lead, dict):
		return {k: v for k, v in lead.items()}
	frappe.throw(_("Invalid lead payload."), frappe.ValidationError)


@frappe.whitelist(methods=["POST"])
def sync_lead(lead=None, property_name: str | None = None, **kwargs):
	"""
	Create or update a **CRM Lead**, optionally linked to a **Property**.

	Request (JSON body): ``{ "lead": { ... }, "property_name": "PROP-..." }``
	You may also pass Property as ``lead.custom_property``, ``lead.property``, or top-level ``property_name``.

	- **Create** requires ``first_name`` and ``email`` (unless updating by ``name``).
	- **Update**: include ``lead.name`` with the existing CRM Lead ID.

	Returns: ``{ "name": "...", "custom_property": "PROP-..." }``
	"""
	frappe.only_for(
		[
			"System Manager",
			"Sales Manager",
			"Agency Admin",
			"Agency Manager",
			"Sales User",
		]
	)

	if lead is None:
		lead = kwargs.get("lead")

	lead_data = _parse_lead_input(lead)

	prop = (property_name or kwargs.get("property_name") or "").strip()
	prop = prop or (lead_data.pop("custom_property", None) or "") or ""
	prop = str(prop).strip() if prop else ""
	if not prop:
		prop = (lead_data.pop("property", None) or lead_data.pop("property_name", None) or "").strip()

	field_pid = _property_fieldname()

	if prop and not frappe.db.exists("Property", prop):
		frappe.throw(_("Property {0} does not exist.").format(prop), frappe.LinkValidationError)

	for k in list(lead_data.keys()):
		if k not in ALLOWED_LEAD_FIELDS and k != "name":
			lead_data.pop(k, None)

	existing = (lead_data.get("name") or "").strip()
	if existing and frappe.db.exists("CRM Lead", existing):
		doc = frappe.get_doc("CRM Lead", existing)
		for k, v in lead_data.items():
			if k == "name":
				continue
			if k in ALLOWED_LEAD_FIELDS:
				setattr(doc, k, v)
		if prop:
			setattr(doc, field_pid, prop)
		doc.flags.ignore_permissions = True
		doc.save()
		return {"name": doc.name, "custom_property": getattr(doc, field_pid, None)}

	missing = [r for r in REQUIRED_FOR_INSERT if not str(lead_data.get(r) or "").strip()]
	if missing:
		frappe.throw(
			_("Missing required lead field(s): {0}").format(", ".join(missing)),
			frappe.ValidationError,
		)

	doc = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			**{k: lead_data[k] for k in ALLOWED_LEAD_FIELDS if k in lead_data},
		}
	)
	if prop:
		setattr(doc, field_pid, prop)
	doc.flags.ignore_permissions = True
	doc.insert()
	return {"name": doc.name, "custom_property": getattr(doc, field_pid, None)}
