from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from . import properties, utils



@frappe.whitelist()
@utils.require_jwt()
def list_favorites() -> list[dict[str, Any]]:
	user = utils.get_current_user()
	return get_favorites_by_user(user)


def get_favorites_by_user(user: str) -> list[dict[str, Any]]:
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
	user = utils.get_current_user()

	property_status = frappe.db.get_value("Property", property_id, "status")
	if not property_status:
		frappe.throw(_("Property does not exist."))
	if property_status != "Active":
		frappe.throw(_("Only active properties can be added to favorites."))

	if frappe.db.exists("Favorite Property", {"user": user, "property": property_id}):
		frappe.response.http_status_code = 200
		return {"message": _("Property is already in favorites.")}

	doc = frappe.get_doc(
		{
			"doctype": "Favorite Property",
			"user": user,
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

