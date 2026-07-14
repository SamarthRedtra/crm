import frappe
from frappe.permissions import has_permission as frappe_has_permission

def get_agency_context(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return None
	
	agency = frappe.db.get_value("Agent", {"user": user}, "agency")
	return agency


def apply_agency_isolation(doctype, user=None):
	if not user:
		user = frappe.session.user
	
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""

	agency = get_agency_context(user)
	if not agency:
		return "1=0" # No agency, no data

	roles = frappe.get_roles(user)
	
	# Agency Admin and Agency Manager can see everything in the agency
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return f"`tab{doctype}`.`agency` = '{agency}'"
	
	# Agent can only see what they created within their agency
	return f"`tab{doctype}`.`agency` = '{agency}' AND `tab{doctype}`.`owner` = '{user}'"

def has_agency_permission(doc, ptype, user=None):
	if not user:
		user = frappe.session.user
	
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	agency = get_agency_context(user)
	if not agency:
		return False
	
	agency_id = getattr(doc, "agency", None)
	if not agency_id and doc.doctype == "Property" and getattr(doc, "agent", None):
		agency_id = frappe.db.get_value("Agent", doc.agent, "agency")
	
	if not agency_id or agency_id != agency:
		return False
	
	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return True
	
	if doc.owner == user:
		return True
		
	return False

# Permission Query Conditions
def get_contact_permission_query(user):
	return apply_agency_isolation("Contact", user)

def get_call_log_permission_query(user):
	return apply_agency_isolation("CRM Call Log", user)

def get_note_permission_query(user):
	return apply_agency_isolation("FCRM Note", user)

# Has Permission hooks
def has_contact_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def has_call_log_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def has_note_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def set_agency_on_doc(doc, method=None):
	if user_can_bypass_isolation(frappe.session.user):
		return

	user = doc.owner or frappe.session.user

	if hasattr(doc, "created_by") and not doc.created_by:
		doc.created_by = user

	if not (hasattr(doc, "agency") and not doc.agency):
		return

	if doc.doctype == "CRM Lead":
		agency = _resolve_lead_agency(doc)
	else:
		agency = frappe.db.get_value("Agent", {"user": user}, "agency")

	if agency:
		doc.agency = agency


def _resolve_lead_agency(doc) -> str | None:
	if getattr(doc, "agent_id", None):
		agency = frappe.db.get_value("Agent", doc.agent_id, "agency")
		if agency:
			return agency

	lead_owner = getattr(doc, "lead_owner", None) or doc.owner
	if lead_owner:
		return frappe.db.get_value("Agent", {"user": lead_owner}, "agency")

	return frappe.db.get_value("Agent", {"user": doc.owner or frappe.session.user}, "agency")

def user_can_bypass_isolation(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)

def has_agency_leadership_role(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return "Agency Admin" in roles or "Agency Manager" in roles

def _property_agency_visibility_sql(agency: str, *, qualified: bool) -> str:
	"""Rows tied to an agency via Property.agency OR via listing agent's Agent.agency."""
	if qualified:
		return (
			f"(`tabProperty`.`agency` = '{agency}' OR "
			f"`tabProperty`.`agent` IN (SELECT `name` FROM `tabAgent` WHERE `agency` = '{agency}'))"
		)
	return (
		f"(agency = '{agency}' OR agent IN (SELECT name FROM `tabAgent` WHERE agency = '{agency}'))"
	)


def get_property_sql_scope_for_user(user):
	"""Returns (sql_where_clause, params) for Property scoping."""
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return "", {}

	agency = get_agency_context(user)
	if not agency:
		return " AND 1=0", {}

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return f" AND {_property_agency_visibility_sql(agency, qualified=False)}", {}

	return f" AND agency = '{agency}' AND owner = '{user}'", {}

# Additional Permission Query Conditions
def get_property_permission_query(user):
	user = user or frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""

	agency = get_agency_context(user)
	if not agency:
		return "1=0"

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return _property_agency_visibility_sql(agency, qualified=True)

	return apply_agency_isolation("Property", user)

def get_agency_billing_invoice_permission_query(user):
	return apply_agency_isolation("Agency Billing Invoice", user)

def get_agency_billing_accrual_permission_query(user):
	return apply_agency_isolation("Agency Billing Accrual", user)

# Additional Has Permission hooks
def has_property_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def has_agency_billing_invoice_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def has_agency_billing_accrual_permission(doc, ptype, user):
	return has_agency_permission(doc, ptype, user)

def _crm_lead_agency_visibility_sql(agency: str) -> str:
	return (
		f"(`tabCRM Lead`.`agency` = '{agency}' OR "
		f"`tabCRM Lead`.`agent_id` IN (SELECT `name` FROM `tabAgent` WHERE `agency` = '{agency}'))"
	)


def get_crm_lead_permission_query(user):
	user = user or frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""

	agency = get_agency_context(user)
	if not agency:
		return "1=0"

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return _crm_lead_agency_visibility_sql(agency)

	return (
		f"(`tabCRM Lead`.`agency` = '{agency}' AND "
		f"(`tabCRM Lead`.`lead_owner` = '{user}' OR `tabCRM Lead`.`owner` = '{user}'))"
	)


def has_crm_lead_permission(doc, ptype, user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	agency = get_agency_context(user)
	if not agency:
		return False

	agency_id = getattr(doc, "agency", None)
	agent_agency = None
	if getattr(doc, "agent_id", None):
		agent_agency = frappe.db.get_value("Agent", doc.agent_id, "agency")
	if not agency_id and agent_agency:
		agency_id = agent_agency

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return agency_id == agency or agent_agency == agency

	if agency_id != agency:
		return False

	lead_owner = getattr(doc, "lead_owner", None)
	return doc.owner == user or lead_owner == user


def _crm_deal_agency_visibility_sql(agency: str) -> str:
	return (
		f"(`tabCRM Deal`.`lead` IN (SELECT `name` FROM `tabCRM Lead` WHERE `agency` = '{agency}') OR "
		f"`tabCRM Deal`.`deal_owner` IN (SELECT `user` FROM `tabAgent` WHERE `agency` = '{agency}'))"
	)


def get_crm_deal_permission_query(user):
	user = user or frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""

	agency = get_agency_context(user)
	if not agency:
		return "1=0"

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return _crm_deal_agency_visibility_sql(agency)

	return (
		f"(`tabCRM Deal`.`deal_owner` = '{user}' AND ("
		f"`tabCRM Deal`.`lead` IN (SELECT `name` FROM `tabCRM Lead` WHERE `agency` = '{agency}') OR "
		f"`tabCRM Deal`.`deal_owner` IN (SELECT `user` FROM `tabAgent` WHERE `agency` = '{agency}')"
		f"))"
	)


def has_crm_deal_permission(doc, ptype, user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	agency = get_agency_context(user)
	if not agency:
		return False

	deal_owner = getattr(doc, "deal_owner", None)
	lead_agency = None
	if getattr(doc, "lead", None):
		lead_agency = frappe.db.get_value("CRM Lead", doc.lead, "agency")
	owner_agency = (
		frappe.db.get_value("Agent", {"user": deal_owner}, "agency") if deal_owner else None
	)
	in_agency = lead_agency == agency or owner_agency == agency

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return in_agency

	return deal_owner == user and in_agency


def _is_internal_manager(user: str | None = None) -> bool:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return user == "Administrator" or bool({"System Manager", "Sales Manager", "Agency Admin", "Agency Manager"} & roles)
