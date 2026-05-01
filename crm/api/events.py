import frappe
from frappe import _

from crm.api.redtra.utils import ensure_customer_for_email


def _parse_if_string(val):
	if isinstance(val, str):
		return frappe.parse_json(val) or {}
	return val or {}


def resolve_customer_from_appointment_payload(ad: dict) -> str | None:
	"""Resolve Customer name from API appointment_data (Customer Link id or email)."""
	ad = ad or {}
	cust = (ad.get("customer") or "").strip()
	if cust:
		if not frappe.db.exists("Customer", cust):
			frappe.throw(_("Customer {0} was not found.").format(cust), frappe.LinkValidationError)
		return cust
	email = (ad.get("customer_email") or "").strip().lower()
	if email:
		return ensure_customer_for_email(email)
	return None


def resolve_customer_for_property_appointment(doc) -> str | None:
	"""Resolve Customer name from transient insert flag, Event custom fields, or email."""
	flag_customer = getattr(doc.flags, "appt_customer", None)
	if flag_customer:
		out = str(flag_customer).strip()
		doc.flags.appt_customer = None
		if out:
			return out

	explicit = (getattr(doc, "appointment_customer", None) or "").strip()
	if explicit:
		if not frappe.db.exists("Customer", explicit):
			frappe.throw(_("Customer {0} was not found.").format(explicit), frappe.LinkValidationError)
		return explicit

	email = (getattr(doc, "customer_email", None) or "").strip().lower()
	if email:
		return ensure_customer_for_email(email)

	return None


def _ensure_property_appointment_for_event(doc) -> None:
	"""Create or update Property Appointment when Event.sync_with_appointment is set."""
	from frappe.utils import cint

	if not cint(getattr(doc, "sync_with_appointment", 0)):
		return

	property_name = getattr(doc, "property", None)
	if not property_name:
		frappe.throw(
			_("Property is required when syncing with Property Appointment."),
			frappe.ValidationError,
		)

	customer_name = resolve_customer_for_property_appointment(doc)
	if not customer_name:
		frappe.throw(
			_("Select an existing customer or enter a customer email."),
			frappe.ValidationError,
		)

	# Event.insert() runs both after_insert and on_update; reference_docname may not be
	# refreshed on the in-memory doc between hooks. Prefer row keyed by calendar_event.
	event_name = getattr(doc, "name", None)
	if event_name:
		linked_appt = frappe.db.get_value(
			"Property Appointment",
			{"calendar_event": event_name},
			"name",
		)
		if linked_appt and frappe.db.exists("Property Appointment", linked_appt):
			apt = frappe.get_doc("Property Appointment", linked_appt)
			apt.property = property_name
			apt.customer = customer_name
			apt.start_datetime = doc.starts_on
			apt.end_datetime = doc.ends_on
			if hasattr(apt, "calendar_event") and getattr(apt, "calendar_event", None) != event_name:
				apt.calendar_event = event_name
			apt.flags.ignore_permissions = True
			apt.save()
			if (
				doc.reference_doctype != "Property Appointment"
				or doc.reference_docname != linked_appt
			):
				frappe.db.set_value(
					"Event",
					doc.name,
					{
						"reference_doctype": "Property Appointment",
						"reference_docname": linked_appt,
					},
					update_modified=False,
				)
			return

	ref_doctype = doc.reference_doctype
	ref_name = doc.reference_docname

	if (
		ref_doctype == "Property Appointment"
		and ref_name
		and frappe.db.exists("Property Appointment", ref_name)
	):
		apt = frappe.get_doc("Property Appointment", ref_name)
		apt.property = property_name
		apt.customer = customer_name
		apt.start_datetime = doc.starts_on
		apt.end_datetime = doc.ends_on
		if hasattr(apt, "calendar_event") and getattr(apt, "calendar_event", None) != doc.name:
			apt.calendar_event = doc.name
		apt.flags.ignore_permissions = True
		apt.save()
		return

	agent = frappe.db.get_value("Agent", {"user": frappe.session.user}, "name")

	apt = frappe.get_doc(
		{
			"doctype": "Property Appointment",
			"property": property_name,
			"customer": customer_name,
			"start_datetime": doc.starts_on,
			"end_datetime": doc.ends_on,
			"status": "Scheduled",
			"agent": agent,
			"calendar_event": doc.name,
			"source": "Web",
		}
	)
	apt.flags.ignore_permissions = True
	apt.insert()

	frappe.db.set_value(
		"Event",
		doc.name,
		{
			"reference_doctype": "Property Appointment",
			"reference_docname": apt.name,
		},
		update_modified=False,
	)


def sync_property_appointment_after_insert(doc, method=None):
	if doc.doctype != "Event":
		return
	_ensure_property_appointment_for_event(doc)


def sync_property_appointment_on_update(doc, method=None):
	if doc.doctype != "Event":
		return
	_ensure_property_appointment_for_event(doc)


@frappe.whitelist()
def create_event_with_appointment(event_data, appointment_data=None):
	"""Insert Event; appointment is created via Event.after_insert hook when sync is enabled."""
	event_data = _parse_if_string(event_data)
	ad = _parse_if_string(appointment_data)

	resolved_customer_for_hook = None
	if ad.get("sync"):
		event_data = dict(event_data)
		event_data["sync_with_appointment"] = 1
		if ad.get("property") and not event_data.get("property"):
			event_data["property"] = ad["property"]
		if ad.get("customer_email") and not event_data.get("customer_email"):
			event_data["customer_email"] = ad["customer_email"]
		if ad.get("customer") and not event_data.get("appointment_customer"):
			event_data["appointment_customer"] = ad["customer"]

		if not event_data.get("property"):
			frappe.throw(
				_("Property is required when syncing with Property Appointment."),
				frappe.ValidationError,
			)
		resolved_customer_for_hook = resolve_customer_from_appointment_payload(ad)
		if not resolved_customer_for_hook:
			frappe.throw(
				_("Select an existing customer or enter a customer email."),
				frappe.ValidationError,
			)

	event = frappe.get_doc(
		{
			"doctype": "Event",
			**event_data,
		}
	)
	if resolved_customer_for_hook:
		event.flags.appt_customer = resolved_customer_for_hook
	event.insert()
	return event
