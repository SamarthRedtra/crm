import frappe
from crm.api.redtra.permissions import apply_agency_isolation

user = 'khansaahmed37@gmail.com'
frappe.set_user(user)
print(f"User: {user}")
print(f"Roles: {frappe.get_roles(user)}")
print(f"Isolation: {apply_agency_isolation('Property', user)}")
print(f"Properties: {frappe.get_list('Property', fields=['name', 'owner', 'agency'])}")
