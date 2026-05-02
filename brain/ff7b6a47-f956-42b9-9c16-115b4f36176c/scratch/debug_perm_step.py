import frappe
from crm.api.redtra.permissions import has_agency_permission, get_agency_context

user = 'khansaahmed37@gmail.com'
docname = 'PROP-2026-00100'
doc = frappe.get_doc('Property', docname)

print(f"User: {user}")
print(f"Roles: {frappe.get_roles(user)}")
agency = get_agency_context(user)
print(f"Agency Context: {agency}")

agency_id = getattr(doc, "agency", None)
print(f"Doc Agency: {agency_id}")

if not agency_id and doc.doctype == "Property" and getattr(doc, "agent", None):
    agency_id = frappe.db.get_value("Agent", doc.agent, "agency")
    print(f"Resolved Doc Agency from Agent: {agency_id}")

print(f"Match: {agency_id == agency}")

res = has_agency_permission(doc, 'read', user)
print(f"Final Result: {res}")
