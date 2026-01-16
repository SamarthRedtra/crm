from __future__ import annotations

import frappe


def execute() -> None:
    _drop_property_code_unique_index()
    _ensure_property_code_limit_setting()


def _drop_property_code_unique_index() -> None:
    if not frappe.db.table_exists("Property"):
        return

    indexes = frappe.db.sql(
        "SHOW INDEX FROM `tabProperty` WHERE Column_name='property_code' AND Non_unique=0",
        as_dict=True,
    )
    for index in indexes:
        key_name = index.get("Key_name")
        if key_name:
            frappe.db.sql(f"ALTER TABLE `tabProperty` DROP INDEX `{key_name}`")


def _ensure_property_code_limit_setting() -> None:
    try:
        current_value = frappe.db.get_single_value(
            "FCRM Settings", "max_agents_per_property_code"
        )
    except Exception:
        current_value = None

    if current_value is None:
        frappe.db.set_single_value("FCRM Settings", "max_agents_per_property_code", 3)




