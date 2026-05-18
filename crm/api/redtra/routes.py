from __future__ import annotations

from werkzeug.routing import Rule

from frappe.api.v1 import url_rules

from . import (
	appointments,
	areas,
	agents,
	agencies,
	auth,
	developers,
	favorites,
	home,
	media,
	notifications,
	push,
	properties,
	transactions,
	amenties,
	reviews,
	reminders,
	icons,
	sid_handler,
)


def register_routes():
	new_rules = [
		Rule("/auth/register", methods=["POST"], endpoint=auth.register),
		Rule("/auth/login", methods=["POST"], endpoint=auth.login),
		Rule("/auth/refresh", methods=["POST"], endpoint=auth.refresh_token),
		Rule("/auth/set-session-from-sid", methods=["GET"], endpoint=sid_handler.set_session_from_sid),
		Rule("/auth/get-sid", methods=["GET"], endpoint=sid_handler.get_sid),
		Rule("/auth/forgot-password", methods=["POST"], endpoint=auth.forgot_password),
		Rule("/auth/logout", methods=["POST"], endpoint=auth.logout),
		Rule("/user/profile", methods=["GET"], endpoint=auth.get_profile),
		Rule("/user/profile", methods=["PUT"], endpoint=auth.update_profile),
		Rule("/user/profile/photo", methods=["POST"], endpoint=media.upload_profile_photo),
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
		Rule(
			"/properties/<string:property_id>/images",
			methods=["POST"],
			endpoint=media.upload_property_image,
		),
		Rule("/developers", methods=["GET"], endpoint=developers.list_developers),
		Rule("/developers", methods=["POST"], endpoint=developers.create_developer),
		Rule(
			"/developers/<string:developer_id>",
			methods=["GET"],
			endpoint=developers.get_developer,
		),
		Rule(
			"/developers/<string:developer_id>/properties",
			methods=["GET"],
			endpoint=developers.list_developer_properties,
		),
		Rule("/notifications", methods=["GET"], endpoint=notifications.list_notifications),
		Rule("/notifications/push/subscribe", methods=["POST"], endpoint=push.subscribe_push_token),
		Rule("/notifications/push/unsubscribe", methods=["POST"], endpoint=push.unsubscribe_push_token),
		Rule("/notifications/push/send", methods=["POST"], endpoint=push.send_push_notification),
		Rule("/notifications/push/send-group", methods=["POST"], endpoint=push.send_group_push_notification),
		Rule(
			"/notifications/mark-read",
			methods=["POST"],
			endpoint=notifications.mark_notifications_read,
		),
		Rule("/favorites", methods=["GET"], endpoint=favorites.list_favorites),
		Rule("/favorites", methods=["POST"], endpoint=favorites.add_favorite),
		Rule(
			"/favorites/<string:property_id>",
			methods=["DELETE"],
			endpoint=favorites.remove_favorite,
		),
		Rule("/transactions", methods=["GET"], endpoint=transactions.list_transactions),
		Rule("/transactions", methods=["POST"], endpoint=transactions.create_transaction),
		Rule(
			"/transactions/<string:transaction_id>",
			methods=["GET"],
			endpoint=transactions.get_transaction,
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
		Rule(
			"/agents/<string:agent_id>/available-slots",
			methods=["GET"],
			endpoint=appointments.get_agent_available_slots,
		),
		Rule("/amenties", methods=["GET"], endpoint=amenties.get_amenities),
		Rule("/agents", methods=["GET"], endpoint=agents.list_agents),
		Rule("/agents/<string:agent_id>", methods=["GET"], endpoint=agents.get_agent),
		Rule("/agencies", methods=["GET"], endpoint=agencies.list_agencies),
		Rule("/agencies/<string:agency_id>", methods=["GET"], endpoint=agencies.get_agency),
		Rule(
			"/agencies/<string:agency_id>/analytics",
			methods=["GET"],
			endpoint=agencies.get_agency_analytics,
		),
		Rule(
			"/agencies/<string:agency_id>/agents",
			methods=["GET"],
			endpoint=agencies.list_agency_agents,
		),
		Rule(
			"/agencies/<string:agency_id>/properties",
			methods=["GET"],
			endpoint=agencies.list_agency_properties,
		),
		Rule(
			"/agencies/<string:agency_id>/profile",
			methods=["GET"],
			endpoint=agencies.get_agency_profile,
		),
		Rule("/agents/<string:agent_id>/reviews", methods=["GET"], endpoint=reviews.get_agent_reviews),
		Rule("/agents/<string:agent_id>/reviews", methods=["POST"], endpoint=reviews.submit_agent_review),
		Rule("/agents/availability", methods=["POST"], endpoint=agents.update_agent_availability),
		Rule(
			"/appointments/<string:appointment_id>/review",
			methods=["POST"],
			endpoint=reviews.submit_appointment_review,
		),
		Rule(
			"/appointments/<string:appointment_id>/review",
			methods=["GET"],
			endpoint=reviews.get_appointment_review,
		),
		Rule(
			"/appointments/<string:appointment_id>/send-reminder",
			methods=["POST"],
			endpoint=reminders.send_appointment_reminder,
		),
		Rule("/home", methods=["GET"], endpoint=home.get_home),
		Rule("/icons/lucide", methods=["GET"], endpoint=icons.list_lucide_icons),
	]

	existing = {(rule.rule, tuple(sorted(rule.methods or []))) for rule in url_rules}
	for rule in new_rules:
		signature = (rule.rule, tuple(sorted(rule.methods or [])))
		if signature not in existing:
			url_rules.append(rule)


register_routes()

