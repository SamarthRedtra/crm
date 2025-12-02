from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from . import properties, utils


@frappe.whitelist()
@utils.require_jwt()
def list_favorites() -> list[dict[str, Any]]:
	user = utils.get_current_user()
	records = frappe.get_all(
		"Favorite Property",
		filters={"user": user},
		fields=["name", "property", "created_at"],
		order_by="created_at desc",
	)

	result = []
	for record in records:
		prop = frappe.get_doc("Property", record.property)
		if prop.status != "Active":
			continue
		result.append(
			{
				"created_at": record.created_at,
				"property": properties.serialize_property_summary(
					{field: getattr(prop, field) for field in properties.SUMMARY_FIELDS}
				),
			}
		)
	return result


@frappe.whitelist()
@utils.require_jwt()
def add_favorite() -> dict[str, Any]:
	data = utils.get_request_json(["property_id"])
	property_id = data["property_id"]

	if not frappe.db.exists("Property", property_id):
		frappe.throw(_("Property does not exist."))

	doc = frappe.get_doc(
		{
			"doctype": "Favorite Property",
			"user": utils.get_current_user(),
			"property": property_id,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.response.http_status_code = 201
	return {"message": _("Property added to favorites.")}


@frappe.whitelist()
@utils.require_jwt()
def remove_favorite(property_id: str) -> dict[str, Any]:
	user = utils.get_current_user()
	name = frappe.db.get_value("Favorite Property", {"user": user, "property": property_id})
	if not name:
		frappe.throw(_("Favorite not found."), frappe.DoesNotExistError)

	frappe.delete_doc("Favorite Property", name, ignore_permissions=True)
	frappe.response.http_status_code = 204
	return {}

