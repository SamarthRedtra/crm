import frappe
from frappe import __dict__ as frappe_dict

_original_get_app_info = frappe.get_app_info

def custom_get_app_info(app_name):
    info = _original_get_app_info(app_name)
    
    # Only override title for "frappe" app
    if app_name == "frappe":
        info["title"] = "Redtra Framework"
    
    return info

def apply():
    frappe_dict["get_app_info"] = custom_get_app_info
