from __future__ import annotations

from werkzeug.routing import Rule

from frappe.api.v1 import url_rules

from . import appointments, areas, auth, favorites, properties


def register_routes():
	new_rules = [
		Rule("/auth/register", methods=["POST"], endpoint=auth.register),
		Rule("/auth/login", methods=["POST"], endpoint=auth.login),
		Rule("/auth/logout", methods=["POST"], endpoint=auth.logout),
		Rule("/user/profile", methods=["GET"], endpoint=auth.get_profile),
		Rule("/user/profile", methods=["PUT"], endpoint=auth.update_profile),
		Rule("/areas", methods=["GET"], endpoint=areas.list_areas),
		Rule("/areas/<string:area_id>", methods=["GET"], endpoint=areas.get_area),
		Rule(
			"/areas/<string:area_id>/properties",
			methods=["GET"],
			endpoint=areas.list_area_properties,
		),
		Rule("/properties", methods=["GET"], endpoint=properties.list_properties),
		Rule("/properties", methods=["POST"], endpoint=properties.create_property),
		Rule("/properties/<string:property_id>", methods=["GET"], endpoint=properties.get_property),
		Rule("/properties/<string:property_id>", methods=["PUT"], endpoint=properties.update_property),
		Rule(
			"/properties/<string:property_id>",
			methods=["DELETE"],
			endpoint=properties.deactivate_property,
		),
		Rule(
			"/properties/<string:property_id>/whatsapp-link",
			methods=["GET"],
			endpoint=properties.get_whatsapp_link,
		),
		Rule("/favorites", methods=["GET"], endpoint=favorites.list_favorites),
		Rule("/favorites", methods=["POST"], endpoint=favorites.add_favorite),
		Rule(
			"/favorites/<string:property_id>",
			methods=["DELETE"],
			endpoint=favorites.remove_favorite,
		),
		Rule("/appointments", methods=["GET"], endpoint=appointments.list_appointments),
		Rule("/appointments", methods=["POST"], endpoint=appointments.create_appointment),
		Rule(
			"/appointments/<string:appointment_id>",
			methods=["GET"],
			endpoint=appointments.get_appointment,
		),
		Rule(
			"/appointments/<string:appointment_id>",
			methods=["PUT"],
			endpoint=appointments.update_appointment,
		),
		Rule(
			"/appointments/<string:appointment_id>",
			methods=["DELETE"],
			endpoint=appointments.cancel_appointment,
		),
	]

	existing = {(rule.rule, tuple(sorted(rule.methods or []))) for rule in url_rules}
	for rule in new_rules:
		signature = (rule.rule, tuple(sorted(rule.methods or [])))
		if signature not in existing:
			url_rules.append(rule)


register_routes()

