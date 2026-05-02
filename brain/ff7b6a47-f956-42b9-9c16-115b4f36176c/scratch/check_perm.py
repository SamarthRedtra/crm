import frappe
user = 'khansaahmed37@gmail.com'
docname = 'PROP-2026-00100'
frappe.set_user(user)
doc = frappe.get_doc('Property', docname)
has_perm = frappe.has_permission(doc.doctype, ptype='read', doc=doc)
print(f"User: {user}")
print(f"Doc: {docname}")
print(f"Doc Agency: {doc.agency}")
print(f"User Agency: {frappe.db.get_value('Agent', {'user': user}, 'agency')}")
print(f"Has Permission: {has_perm}")
