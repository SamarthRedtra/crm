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
			apt.flags.skip_sync_to_event = True
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
		apt.flags.skip_sync_to_event = True
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


def _sync_linked_appointment_from_calendar_event(doc) -> None:
	"""When a calendar Event moves or is cancelled, update the Property Appointment (reverse sync)."""
	from frappe.utils import cint

	if doc.doctype != "Event":
		return
	if getattr(doc.flags, "from_property_appointment_sync", False):
		return
	if cint(getattr(doc, "sync_with_appointment", 0)):
		# The dedicated appointment payload path updates the appointment in _ensure_property_appointment_for_event
		return

	appt_name = None
	if doc.reference_doctype == "Property Appointment" and doc.reference_docname:
		appt_name = doc.reference_docname
	if not appt_name:
		appt_name = frappe.db.get_value("Property Appointment", {"calendar_event": doc.name}, "name")
	if not appt_name or not frappe.db.exists("Property Appointment", appt_name):
		return

	apt = frappe.get_doc("Property Appointment", appt_name)
	if apt.status != "Scheduled":
		return

	changed = False
	if doc.status == "Cancelled" and apt.status == "Scheduled":
		apt.status = "Cancelled"
		changed = True
	elif doc.starts_on and doc.ends_on:
		if str(apt.start_datetime) != str(doc.starts_on) or str(apt.end_datetime) != str(doc.ends_on):
			apt.start_datetime = doc.starts_on
			apt.end_datetime = doc.ends_on
			changed = True

	prop = getattr(doc, "property", None)
	if prop and apt.property != prop:
		apt.property = prop
		changed = True

	if not changed:
		return

	apt.flags.ignore_permissions = True
	apt.flags.skip_sync_to_event = True
	apt.save(ignore_permissions=True)


CALENDAR_EVENT_FIELDS = [
	"name",
	"status",
	"subject",
	"description",
	"starts_on",
	"ends_on",
	"all_day",
	"event_type",
	"color",
	"reference_doctype",
	"reference_docname",
	"sync_with_appointment",
	"customer_email",
	"appointment_customer",
	"property",
	"owner",
]


@frappe.whitelist()
def get_calendar_events(
	doctype=None,
	fields=None,
	filters=None,
	or_filters=None,
	order_by=None,
	start=None,
	limit_start=None,
	limit_page_length=None,
	limiter=None,
	parent=None,
	debug=None,
	**kwargs,
):
	"""Return Open events owned by the current user or tied to a Property Appointment where they are the agent."""
	user = frappe.session.user
	if user == "Guest":
		return []

	meta = frappe.get_meta("Event")
	field_list = CALENDAR_EVENT_FIELDS
	if isinstance(fields, (list, tuple)) and fields:
		field_list = [f for f in fields if meta.has_field(f) or f in ("name",)]

	owned = frappe.get_all(
		"Event",
		filters={"status": "Open", "owner": user},
		pluck="name",
	)

	agent_linked = frappe.sql(
		"""
		select e.name
		from `tabEvent` e
		inner join `tabProperty Appointment` a on a.calendar_event = e.name
		inner join `tabAgent` ag on ag.name = a.agent
		where e.status = 'Open' and ag.`user` = %s
		""",
		user,
	)
	agent_names = {row[0] for row in (agent_linked or [])}

	all_names = list(set(owned) | agent_names)
	if not all_names:
		return []

	return frappe.get_list(
		"Event",
		filters={"name": ["in", all_names]},
		fields=field_list,
		order_by="starts_on asc",
		limit_page_length=9999,
	)


def _user_can_delete_calendar_event(event_doc) -> bool:
	user = frappe.session.user
	if user == "Administrator":
		return True
	if event_doc.owner == user:
		return True
	roles = set(frappe.get_roles(user))
	if "System Manager" in roles or "Sales Manager" in roles:
		return True

	agent_row = frappe.db.get_value(
		"Property Appointment",
		{"calendar_event": event_doc.name},
		["name", "agent"],
		as_dict=True,
	)
	if agent_row and agent_row.agent:
		agent_user = frappe.db.get_value("Agent", agent_row.agent, "user")
		if agent_user == user:
			return True

	if event_doc.reference_doctype == "Property Appointment" and event_doc.reference_docname:
		agent = frappe.db.get_value("Property Appointment", event_doc.reference_docname, "agent")
		if agent:
			agent_user = frappe.db.get_value("Agent", agent, "user")
			if agent_user == user:
				return True

	return False


@frappe.whitelist()
def delete_calendar_event(name: str | None = None):
	"""Delete an Event from the CRM calendar with Property-appointment-aware permission checks."""
	name = (name or frappe.form_dict.get("name") or "").strip()
	if not name:
		frappe.throw(_("Event name is required."))

	if not frappe.db.exists("Event", name):
		frappe.throw(_("Event {0} was not found.").format(name), frappe.DoesNotExistError)

	doc = frappe.get_doc("Event", name)
	if not _user_can_delete_calendar_event(doc):
		frappe.throw(_("Not permitted to delete this event."), frappe.PermissionError)

	frappe.delete_doc("Event", name, ignore_permissions=True, force=1)
	return {"ok": True, "name": name}


def cancel_property_appointment_on_event_delete(doc, method=None):
	"""When an Event is deleted from the calendar, cancel the linked Property Appointment."""
	if doc.doctype != "Event":
		return

	appt_name = frappe.db.get_value("Property Appointment", {"calendar_event": doc.name}, "name")
	if not appt_name and doc.reference_doctype == "Property Appointment" and doc.reference_docname:
		appt_name = doc.reference_docname

	if not appt_name or not frappe.db.exists("Property Appointment", appt_name):
		return

	status = frappe.db.get_value("Property Appointment", appt_name, "status")
	if status != "Scheduled":
		return

	apt = frappe.get_doc("Property Appointment", appt_name)
	apt.status = "Cancelled"
	apt.flags.ignore_permissions = True
	apt.flags.skip_sync_to_event = True
	apt.save(ignore_permissions=True)


def sync_property_appointment_after_insert(doc, method=None):
	if doc.doctype != "Event":
		return
	_ensure_property_appointment_for_event(doc)


def sync_property_appointment_on_update(doc, method=None):
	if doc.doctype != "Event":
		return
	_ensure_property_appointment_for_event(doc)
	_sync_linked_appointment_from_calendar_event(doc)


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
