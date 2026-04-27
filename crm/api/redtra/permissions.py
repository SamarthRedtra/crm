import frappe
from frappe.permissions import has_permission as frappe_has_permission

def get_agency_context():
	if frappe.session.user == "Administrator":
		return None
	
	agency = frappe.db.get_value("Agent", {"user": frappe.session.user}, "agency")
	return agency

def apply_agency_isolation(doctype, user=None):
	if not user:
		user = frappe.session.user
	
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""

	agency = get_agency_context()
	if not agency:
		return "1=0" # No agency, no data

	roles = frappe.get_roles(user)
	
	# Agency Admin and Agency Manager can see everything in the agency
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return f"`agency` = '{agency}'"
	
	# Agent can only see what they created within their agency
	return f"`agency` = '{agency}' AND `owner` = '{user}'"

def has_agency_permission(doc, ptype, user=None):
	if not user:
		user = frappe.session.user
	
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	agency = get_agency_context()
	if not agency:
		return False
	
	if doc.agency != agency:
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
	if not user_can_bypass_isolation(frappe.session.user):
		user = doc.owner or frappe.session.user
		
		if hasattr(doc, "created_by") and not doc.created_by:
			doc.created_by = user

		if hasattr(doc, "agency") and not doc.agency:
			agency = frappe.db.get_value("Agent", {"user": user}, "agency")
			if agency:
				doc.agency = agency

def user_can_bypass_isolation(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)

def has_agency_leadership_role(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return "Agency Admin" in roles or "Agency Manager" in roles

def get_property_sql_scope_for_user(user):
	"""Returns (sql_where_clause, params) for Property scoping."""
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return "", {}

	agency = get_agency_context()
	if not agency:
		return " AND 1=0", {}

	roles = frappe.get_roles(user)
	if "Agency Admin" in roles or "Agency Manager" in roles:
		return f" AND agency = '{agency}'", {}

	return f" AND agency = '{agency}' AND owner = '{user}'", {}
