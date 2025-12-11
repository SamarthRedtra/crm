from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


FIELD_DEFINITION = {
    "User": [
        {
            "fieldname": "remember_me_opt_in",
            "label": "Remember Me",
            "fieldtype": "Check",
            "insert_after": "last_ip",
            "default": 0,
            "read_only": 0,
            "description": "User opted to be remembered during authentication.",
        }
    ]
}


def execute() -> None:
    if frappe.db.field_exists("User", "remember_me_opt_in"):
        return

    create_custom_fields(FIELD_DEFINITION, ignore_validate=True)
