from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document


class Area(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		area_name: DF.Data
		city: DF.Data | None
		country: DF.Link | None
		geo_json: DF.LongText | None
		latitude: DF.Float
		longitude: DF.Float
		pincode: DF.Data | None
		state: DF.Data | None
	# end: auto-generated types

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

