from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class AgencyTeamInvitation(Document):
	def validate(self):
		validate_email_address(self.email, True)
		if self.agency_role not in {"Agent", "Manager", "Admin"}:
			frappe.throw(_("Invalid agency role."))

	def before_insert(self):
		self.key = frappe.generate_hash(length=16)
		self.invited_by = frappe.session.user
		self.status = "Pending"

	def after_insert(self):
		self._send_email()

	def _send_email(self):
		link = frappe.utils.get_url(f"/api/method/crm.api.redtra.agency_invites.accept_agency_team_invitation?key={self.key}")
		title = "Frappe CRM"
		try:
			frappe.sendmail(
				recipients=[self.email],
				subject=_("You have been invited to join an agency on {0}").format(title),
				template="crm_invitation",
				args={"title": title, "invite_link": link},
				now=True,
			)
			self.db_set("email_sent_at", frappe.utils.now())
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Agency team invitation email failed")
