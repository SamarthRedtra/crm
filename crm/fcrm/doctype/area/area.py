from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document


class Area(Document):
	def validate(self):
		self._validate_coordinates()
		self._validate_geojson()

	def _validate_coordinates(self):
		if self.latitude is not None and (self.latitude < -90 or self.latitude > 90):
			frappe.throw(_("Latitude must be between -90 and 90 degrees."))
		if self.longitude is not None and (self.longitude < -180 or self.longitude > 180):
			frappe.throw(_("Longitude must be between -180 and 180 degrees."))

	def _validate_geojson(self):
		if not self.geo_json:
			return

		try:
			json.loads(self.geo_json)
		except json.JSONDecodeError as exc:
			frappe.throw(_("GeoJSON must be a valid JSON string."), exc=exc)

