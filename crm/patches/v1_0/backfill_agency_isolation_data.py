from __future__ import annotations

import frappe
from frappe.permissions import add_user_permission


def execute():
	summary = {
		"property_updated": _backfill_property_agency(),
		"crm_lead_from_agent": _backfill_crm_lead_agency_from_agent(),
		"crm_lead_from_owner": _backfill_crm_lead_agency_from_owner(),
		"contact_from_owner": _backfill_owner_agency("Contact"),
		"contact_from_created_by": _backfill_contact_agency_from_created_by(),
		"fcrm_note_updated": _backfill_owner_agency("FCRM Note"),
		"crm_call_log_updated": _backfill_owner_agency("CRM Call Log"),
		"user_permissions_created": _backfill_agent_user_permissions(),
	}
	summary["remaining_missing_agency"] = _count_missing_agency()
	summary["agents_missing_user_permission"] = _count_agents_missing_user_permission()

	frappe.log_error(
		title="Agency isolation backfill summary",
		message=frappe.as_json(summary, indent=2),
	)
	print(frappe.as_json(summary, indent=2))
	frappe.db.commit()


def _backfill_property_agency() -> int:
	return _rowcount_from_update(
		"""
		UPDATE `tabProperty` p
		INNER JOIN `tabAgent` a ON p.agent = a.name
		SET p.agency = a.agency
		WHERE a.agency IS NOT NULL AND a.agency != ''
		  AND (p.agency IS NULL OR p.agency = '' OR p.agency != a.agency)
		"""
	)


def _backfill_crm_lead_agency_from_agent() -> int:
	return _rowcount_from_update(
		"""
		UPDATE `tabCRM Lead` l
		INNER JOIN `tabAgent` a ON l.agent_id = a.name
		SET l.agency = a.agency
		WHERE a.agency IS NOT NULL AND a.agency != ''
		  AND (l.agency IS NULL OR l.agency = '' OR l.agency != a.agency)
		"""
	)


def _backfill_crm_lead_agency_from_owner() -> int:
	return _rowcount_from_update(
		"""
		UPDATE `tabCRM Lead` l
		INNER JOIN `tabAgent` a ON l.lead_owner = a.user
		SET l.agency = a.agency
		WHERE a.agency IS NOT NULL AND a.agency != ''
		  AND (l.agency IS NULL OR l.agency = '')
		"""
	)


def _backfill_owner_agency(doctype: str) -> int:
	table = f"tab{doctype}"
	if not frappe.db.has_column(doctype, "agency"):
		return 0

	return _rowcount_from_update(
		f"""
		UPDATE `{table}` d
		INNER JOIN `tabAgent` a ON d.owner = a.user
		SET d.agency = a.agency
		WHERE a.agency IS NOT NULL AND a.agency != ''
		  AND (d.agency IS NULL OR d.agency = '' OR d.agency != a.agency)
		"""
	)


def _backfill_contact_agency_from_created_by() -> int:
	if not frappe.db.has_column("Contact", "created_by"):
		return 0

	return _rowcount_from_update(
		"""
		UPDATE `tabContact` d
		INNER JOIN `tabAgent` a ON d.created_by = a.user
		SET d.agency = a.agency
		WHERE a.agency IS NOT NULL AND a.agency != ''
		  AND (d.agency IS NULL OR d.agency = '')
		"""
	)


def _backfill_agent_user_permissions() -> int:
	from frappe.core.doctype.user_permission.user_permission import user_permission_exists

	created = 0
	agents = frappe.get_all(
		"Agent",
		filters={"agency": ["is", "set"], "user": ["is", "set"]},
		fields=["name", "user", "agency"],
	)
	for agent in agents:
		if user_permission_exists(agent.user, "Agency", agent.agency, None):
			continue
		add_user_permission("Agency", agent.agency, agent.user, ignore_permissions=True)
		created += 1
	return created


def _count_missing_agency() -> dict[str, int]:
	counts: dict[str, int] = {}
	for doctype in ("Property", "CRM Lead", "Contact", "FCRM Note", "CRM Call Log"):
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		if not frappe.db.has_column(doctype, "agency"):
			continue
		counts[doctype] = frappe.db.count(
			doctype,
			filters={"agency": ["in", ["", None]]},
		)
	return counts


def _count_agents_missing_user_permission() -> int:
	from frappe.core.doctype.user_permission.user_permission import user_permission_exists

	missing = 0
	agents = frappe.get_all(
		"Agent",
		filters={"agency": ["is", "set"], "user": ["is", "set"]},
		fields=["user", "agency"],
	)
	for agent in agents:
		if not user_permission_exists(agent.user, "Agency", agent.agency, None):
			missing += 1
	return missing


def _rowcount_from_update(query: str) -> int:
	frappe.db.sql(query)
	return frappe.db.sql("SELECT ROW_COUNT()")[0][0]
