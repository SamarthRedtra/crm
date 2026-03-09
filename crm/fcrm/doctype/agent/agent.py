from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class Agent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from crm.fcrm.doctype.agent_availability_slot.agent_availability_slot import AgentAvailabilitySlot
		from crm.fcrm.doctype.agent_kyc_document.agent_kyc_document import AgentKYCDocument
		from frappe.types import DF

		agency: DF.Link | None
		availability_slots: DF.Table[AgentAvailabilitySlot]
		bio: DF.SmallText | None
		brn_id: DF.Data | None
		dfd_registration_id: DF.Data
		email: DF.Data | None
		full_name: DF.Data | None
		kyc_documents: DF.Table[AgentKYCDocument]
		max_appointment_minutes: DF.Int
		max_daily_appointments: DF.Int
		phone: DF.Data | None
		profile_image: DF.AttachImage | None
		status: DF.Literal["Draft", "Pending Verification", "Verified", "Rejected"]
		user: DF.Link
		whatsapp_number: DF.Data | None
	# end: auto-generated types

	STATUS_FLOW = {
		"Draft": {"Draft", "Pending Verification"},
		"Pending Verification": {"Draft", "Pending Verification", "Verified", "Rejected"},
		"Verified": {"Pending Verification", "Verified"},
		"Rejected": {"Draft", "Pending Verification", "Rejected"},
	}

	def validate(self):
		self._sync_user_details()
		self._validate_status_transition()
		self._validate_daily_limit()

	def after_save(self):
		self._attach_kyc_files_to_doc()

	def _sync_user_details(self):
		if not self.user:
			return

		try:
			user_doc = frappe.get_cached_doc("User", self.user)
		except frappe.DoesNotExistError as exc:
			frappe.throw(_("Linked user {0} does not exist.").format(self.user), exc=exc)

		if not user_doc.enabled:
			frappe.throw(_("Linked user {0} is disabled.").format(self.user))

		self.full_name = user_doc.full_name
		self.email = user_doc.email or user_doc.user_email

	def _validate_status_transition(self):
		if self.is_new():
			return

		previous_status = self.get_db_value("status")
		if not previous_status:
			return

		allowed = self.STATUS_FLOW.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Invalid status change from {0} to {1}.").format(previous_status, self.status)
			)

	def _validate_daily_limit(self):
		if self.max_daily_appointments is not None and self.max_daily_appointments < 0:
			frappe.throw(_("Max daily appointments cannot be negative."))

	def _attach_kyc_files_to_doc(self):
		"""Ensure every KYC document file is also attached to the parent Agent doc."""
		if not self.kyc_documents:
			return

		existing_attachments = set(
			frappe.db.get_all(
				"File",
				filters={"attached_to_doctype": "Agent", "attached_to_name": self.name},
				pluck="file_url",
			)
		)

		for row in self.kyc_documents:
			if not row.document_file:
				continue
			if row.document_file in existing_attachments:
				continue
			try:
				file_doc = frappe.get_doc(
					{
						"doctype": "File",
						"file_url": row.document_file,
						"attached_to_doctype": "Agent",
						"attached_to_name": self.name,
						"attached_to_field": "kyc_documents",
						"is_private": 1,
					}
				)
				file_doc.flags.ignore_permissions = True
				file_doc.insert()
				existing_attachments.add(row.document_file)
			except Exception:
				pass  # file may already be registered; skip silently


@frappe.whitelist()
def review_kyc_document(agent_name, row_name, action, comment=""):
	"""
	Allow admin to Approve or Reject an individual KYC document.
	action: 'Approved' | 'Rejected'
	"""
	frappe.only_for(["System Manager", "Sales Manager"])

	agent = frappe.get_doc("Agent", agent_name)
	doc_row = None
	for row in agent.kyc_documents:
		if row.name == row_name:
			doc_row = row
			break

	if not doc_row:
		frappe.throw(_("KYC Document row not found."))

	if action not in ("Approved", "Rejected"):
		frappe.throw(_("Invalid action. Use 'Approved' or 'Rejected'."))

	doc_row.doc_status = action
	doc_row.verified = 1 if action == "Approved" else 0
	doc_row.admin_comment = comment

	# If all docs approved → Verified; if any rejected → Rejected
	all_statuses = [r.doc_status for r in agent.kyc_documents]
	if all(s == "Approved" for s in all_statuses):
		agent.status = "Verified"
	elif any(s == "Rejected" for s in all_statuses):
		agent.status = "Rejected"

	agent.flags.ignore_permissions = True
	agent.save()

	return {"status": agent.status, "doc_status": doc_row.doc_status}


@frappe.whitelist()
def get_mandatory_kyc_doc_types():
	"""Return the list of mandatory KYC document types from FCRM Settings."""
	settings = frappe.get_single("FCRM Settings")
	raw = getattr(settings, "mandatory_kyc_documents", "") or ""
	# stored as comma-separated values
	types = [t.strip() for t in raw.split(",") if t.strip()]
	return types
