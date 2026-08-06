from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe import client
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime

from crm.api import events


class TestCalendarEventHistory(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.event_names = []
		self.global_search_patch = patch("frappe.model.document.update_global_search")
		self.global_search_patch.start()

	def tearDown(self):
		frappe.set_user("Administrator")
		if self.event_names:
			frappe.db.delete("Event", {"name": ["in", self.event_names]})
		frappe.db.commit()
		self.global_search_patch.stop()

	def make_event(self, *, starts_on, ends_on, all_day=False):
		doc = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"Calendar history {frappe.generate_hash(length=8)}",
				"event_category": "Meeting",
				"starts_on": starts_on,
				"ends_on": ends_on,
				"all_day": all_day,
				"status": "Open",
			}
		).insert(ignore_permissions=True)
		self.event_names.append(doc.name)
		return doc

	def test_timed_past_event_cannot_be_saved_or_deleted(self):
		now = now_datetime()
		doc = self.make_event(
			starts_on=now - timedelta(hours=2),
			ends_on=now - timedelta(hours=1),
		)

		doc.subject = "Changed historical event"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			client.set_value("Event", doc.name, {"subject": "Changed through client API"})

		with self.assertRaises(frappe.ValidationError):
			events.delete_calendar_event(doc.name)

	def test_all_day_event_is_past_after_its_end_date(self):
		now = now_datetime()
		past_day = now.date() - timedelta(days=1)
		doc = self.make_event(
			starts_on=get_datetime(f"{past_day} 00:00:00"),
			ends_on=get_datetime(f"{past_day} 23:59:59"),
			all_day=True,
		)

		self.assertTrue(events.is_past_calendar_event(doc))
		doc.subject = "Changed historical all-day event"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_future_event_can_be_changed(self):
		now = now_datetime()
		doc = self.make_event(
			starts_on=now + timedelta(hours=1),
			ends_on=now + timedelta(hours=2),
		)

		doc.subject = "Updated future event"
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Event", doc.name, "subject"), "Updated future event")
