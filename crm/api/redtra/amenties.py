import frappe
from typing import Any


@frappe.whitelist(allow_guest=True)
def get_amenities() -> dict[str, Any]:
    return frappe.get_all("Amenity", fields=["name"])