from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import utils

_ANONYMOUS_REVIEWER_USER = "redtra.public.reviewer@anonymous.local"


def _get_anonymous_reviewer_customer() -> str:
	"""Shared Customer used when a review is submitted without a logged-in CRM customer."""
	if frappe.db.exists("Customer", _ANONYMOUS_REVIEWER_USER):
		return _ANONYMOUS_REVIEWER_USER
	if not frappe.db.exists("User", _ANONYMOUS_REVIEWER_USER):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": _ANONYMOUS_REVIEWER_USER,
				"first_name": "Public",
				"last_name": "Reviewer",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Customer",
			"user": _ANONYMOUS_REVIEWER_USER,
			"full_name": "Anonymous Reviewer",
		}
	).insert(ignore_permissions=True)
	return _ANONYMOUS_REVIEWER_USER


def _resolve_reviewer_name(customer_id: str | None, guest_display_name: str | None) -> str | None:
	label = (guest_display_name or "").strip()
	if label:
		return label
	if customer_id:
		return frappe.db.get_value("Customer", customer_id, "full_name")
	return None


@frappe.whitelist()
@utils.require_jwt()
def submit_appointment_review(appointment_id: str) -> dict[str, Any]:
	"""
	Submit a review and rating for a completed appointment.
	
	Only the customer who booked the appointment can submit a review.
	One review per appointment is allowed.
	"""
	data = utils.get_request_json()
	
	# Get appointment details
	appointment_doc = frappe.get_doc("Property Appointment", appointment_id)
	
	# Verify appointment is completed
	if appointment_doc.status != "Completed":
		frappe.throw(
			_("Reviews can only be submitted for completed appointments."),
			frappe.ValidationError
		)
	
	# Verify customer access
	current_user = utils.get_current_user()
	customer = utils.get_customer_by_user(current_user)
	if not customer:
		frappe.throw(_("Customer profile is required to submit reviews."), frappe.PermissionError)
	
	if appointment_doc.customer != customer.name:
		frappe.throw(
			_("You can only review appointments that you booked."),
			frappe.PermissionError
		)
	
	# Check if review already exists
	existing_review = frappe.db.get_value(
		"Review and Rating",
		{"appointment": appointment_id},
		"name"
	)
	
	if existing_review:
		# Update existing review
		review_doc = frappe.get_doc("Review and Rating", existing_review)
	else:
		# Create new review
		review_doc = frappe.get_doc({
			"doctype": "Review and Rating",
			"appointment": appointment_id,
			"agent": appointment_doc.agent,
			"property": appointment_doc.property,
			"customer": customer.name,
			"status": "Draft",
		})
	
	# Update review fields
	if "overall_rating" in data:
		review_doc.overall_rating = _normalize_rating_input(data.get("overall_rating", 0))
	if "agent_rating" in data:
		review_doc.agent_rating = _normalize_rating_input(data.get("agent_rating", 0))
	if "property_rating" in data:
		review_doc.property_rating = _normalize_rating_input(data.get("property_rating", 0))
	if "review_text" in data:
		review_doc.review_text = data.get("review_text", "")
	
	# Set status to Submitted
	review_doc.status = "Submitted"
	
	review_doc.save(ignore_permissions=True)
	frappe.db.commit()
	
	return serialize_review(review_doc.name)


@frappe.whitelist(allow_guest=True)
def submit_agent_review(agent_id: str) -> dict[str, Any]:
	"""Submit a review for an agent (without appointment)"""
	return _submit_general_review(agent_id=agent_id)


@frappe.whitelist(allow_guest=True)
def submit_property_review(property_id: str) -> dict[str, Any]:
	"""Submit a review for a property (without appointment)"""
	return _submit_general_review(property_id=property_id)


def _submit_general_review(agent_id: str | None = None, property_id: str | None = None) -> dict[str, Any]:
	data = utils.get_request_json()
	current_user = utils.get_current_user()
	customer = utils.get_customer_by_user(current_user)
	guest_label = (data.get("reviewer_name") or data.get("guest_display_name") or "").strip()

	if not customer:
		customer_name = _get_anonymous_reviewer_customer()
	else:
		customer_name = customer.name

	if agent_id:
		# Resolve agent ID (could be BRN)
		agent_name = frappe.db.get_value("Agent", {"dfd_registration_id": agent_id}, "name")
		if agent_name:
			agent_id = agent_name
		# Ensure agent exists
		if not frappe.db.exists("Agent", agent_id):
			frappe.throw(_("Agent not found."), frappe.DoesNotExistError)
	elif property_id:
		# Ensure property exists
		if not frappe.db.exists("Property", property_id):
			frappe.throw(_("Property not found."), frappe.DoesNotExistError)
	else:
		frappe.throw(_("Target is required."), frappe.ValidationError)

	# Always create a new review record instead of updating existing ones
	review_doc = frappe.new_doc("Review and Rating")
	review_doc.customer = customer_name
	if not customer and guest_label:
		review_doc.guest_display_name = guest_label
	if agent_id:
		review_doc.agent = agent_id
	if property_id:
		review_doc.property = property_id
	review_doc.status = "Draft"

	if "overall_rating" in data:
		review_doc.overall_rating = _normalize_rating_input(data.get("overall_rating", 0))
	if "agent_rating" in data:
		review_doc.agent_rating = _normalize_rating_input(data.get("agent_rating", 0))
	if "property_rating" in data:
		review_doc.property_rating = _normalize_rating_input(data.get("property_rating", 0))
	if "review_text" in data:
		review_doc.review_text = data.get("review_text", "")

	review_doc.status = "Submitted"
	if not review_doc.submitted_at:
		from frappe.utils import now_datetime
		review_doc.submitted_at = now_datetime()
		
	review_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return serialize_review(review_doc.name)

@frappe.whitelist()
@utils.require_jwt()
def get_appointment_review(appointment_id: str) -> dict[str, Any] | None:
	"""Get review for a specific appointment (if exists)"""
	current_user = utils.get_current_user()
	customer = utils.get_customer_by_user(current_user)
	
	if not customer:
		return None
	
	# Verify customer owns the appointment
	appointment_customer = frappe.db.get_value("Property Appointment", appointment_id, "customer")
	if appointment_customer != customer.name:
		frappe.throw(
			_("You can only view reviews for your own appointments."),
			frappe.PermissionError
		)
	
	review_name = frappe.db.get_value(
		"Review and Rating",
		{"appointment": appointment_id},
		"name"
	)
	
	if review_name:
		return serialize_review(review_name)
	
	return None


def serialize_review(review_name: str) -> dict[str, Any]:
	"""Serialize review document for API response"""
	review_doc = frappe.get_doc("Review and Rating", review_name)
	
	reviewer_name = _resolve_reviewer_name(
		review_doc.customer, getattr(review_doc, "guest_display_name", None)
	)
	
	return {
		"id": review_doc.name,
		"appointment_id": review_doc.appointment,
		"agent_id": review_doc.agent,
		"property_id": review_doc.property,
		"customer_id": review_doc.customer,
		"reviewer_name": reviewer_name,
		"overall_rating": _denormalize_rating(review_doc.overall_rating),
		"agent_rating": _denormalize_rating(review_doc.agent_rating),
		"property_rating": _denormalize_rating(review_doc.property_rating),
		"review_text": review_doc.review_text or "",
		"status": review_doc.status,
		"submitted_at": review_doc.submitted_at,
		"created_at": review_doc.creation,
	}


def empty_agent_rating_summary() -> dict[str, Any]:
	"""Default shape for agent ratings (averages + empty review list)."""
	return {
		"average_overall_rating": 0.0,
		"average_agent_rating": 0.0,
		"average_property_rating": 0.0,
		"total_reviews": 0,
		"recent_reviews": [],
	}


def _stats_from_aggregate_row(row: dict[str, Any]) -> dict[str, Any]:
	cnt = int(row.get("cnt") or 0)
	if cnt <= 0:
		return empty_agent_rating_summary()
	ao = float(row.get("avg_overall") or 0)
	aa = float(row.get("avg_agent") or 0)
	ap = float(row.get("avg_property") or 0)
	return {
		"average_overall_rating": round(ao * 5, 2),
		"average_agent_rating": round(aa * 5, 2),
		"average_property_rating": round(ap * 5, 2),
		"total_reviews": cnt,
		"recent_reviews": [],
	}


def get_agent_rating_stats_summary_only(agent_id: str) -> dict[str, Any]:
	"""Averages and counts only (no per-review rows). Uses one SQL aggregate."""
	if not agent_id:
		return empty_agent_rating_summary()
	rows = frappe.db.sql(
		"""
		SELECT
			COUNT(*) AS cnt,
			AVG(overall_rating) AS avg_overall,
			AVG(agent_rating) AS avg_agent,
			AVG(property_rating) AS avg_property
		FROM `tabReview and Rating`
		WHERE agent = %s
			AND status IN ('Submitted', 'Published')
		""",
		(agent_id,),
		as_dict=True,
	)
	if not rows:
		return empty_agent_rating_summary()
	return _stats_from_aggregate_row(rows[0])


def get_agent_rating_stats_batch(agent_ids: list[str]) -> dict[str, dict[str, Any]]:
	"""Summary-only stats for many agents (one grouped SQL query)."""
	seen: list[str] = []
	for a in agent_ids:
		if a and a not in seen:
			seen.append(a)
	if not seen:
		return {}
	placeholders = ", ".join(["%s"] * len(seen))
	rows = frappe.db.sql(
		f"""
		SELECT
			agent,
			COUNT(*) AS cnt,
			AVG(overall_rating) AS avg_overall,
			AVG(agent_rating) AS avg_agent,
			AVG(property_rating) AS avg_property
		FROM `tabReview and Rating`
		WHERE status IN ('Submitted', 'Published')
			AND agent IN ({placeholders})
		GROUP BY agent
		""",
		tuple(seen),
		as_dict=True,
	)
	by_agent = {r["agent"]: _stats_from_aggregate_row(r) for r in rows if r.get("agent")}
	return {aid: by_agent.get(aid, empty_agent_rating_summary()) for aid in seen}


def get_agent_rating_stats(agent_id: str, *, include_review_items: bool = True) -> dict[str, Any]:
	"""Get rating statistics for an agent."""
	if not include_review_items:
		return get_agent_rating_stats_summary_only(agent_id)
	reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"agent": agent_id,
			"status": ["in", ["Submitted", "Published"]],
		},
		fields=[
			"name",
			"overall_rating",
			"agent_rating",
			"property_rating",
			"review_text",
			"creation",
			"customer",
			"guest_display_name",
			"property",
			"appointment",
		],
		order_by="creation desc",
		ignore_permissions=True,
	)

	if not reviews:
		return empty_agent_rating_summary()

	total_count = len(reviews)
	overall_sum = sum(float(r.get("overall_rating") or 0) for r in reviews)
	agent_sum = sum(float(r.get("agent_rating") or 0) for r in reviews)
	property_sum = sum(float(r.get("property_rating") or 0) for r in reviews)

	recent_reviews = []
	for review in reviews:
		recent_reviews.append(
			{
				"id": review.get("name"),
				"overall_rating": _denormalize_rating(review.get("overall_rating")),
				"agent_rating": _denormalize_rating(review.get("agent_rating")),
				"property_rating": _denormalize_rating(review.get("property_rating")),
				"review_text": review.get("review_text") or "",
				"reviewer_name": _resolve_reviewer_name(
					review.get("customer"), review.get("guest_display_name")
				),
				"property_title": frappe.db.get_value("Property", review.get("property"), "title")
				if review.get("property")
				else None,
				"appointment_id": review.get("appointment"),
				"created_at": review.get("creation"),
			}
		)

	return {
		"average_overall_rating": round((overall_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"average_agent_rating": round((agent_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"average_property_rating": round((property_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"total_reviews": total_count,
		"recent_reviews": recent_reviews,
	}


@frappe.whitelist(allow_guest=True)
def get_agent_reviews(agent_id: str) -> dict[str, Any]:
	"""
	Public API to get reviews for an agent - no authentication required
	
	Returns paginated list of reviews with rating statistics.
	"""
	# Resolve agent ID (could be name or BRN)
	from . import agents
	agent_name = frappe.db.get_value("Agent", {"dfd_registration_id": agent_id}, "name")
	if not agent_name:
		agent_name = frappe.db.get_value("Agent", {"name": agent_id}, "name")
	
	if not agent_name:
		frappe.throw(_("Agent not found."), frappe.DoesNotExistError)
	
	current_agent_id = agent_name
	
	# Get pagination parameters
	page = max(1, cint(frappe.form_dict.get("page") or 1))
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size
	
	# Get rating statistics (includes recent reviews)
	rating_stats = get_agent_rating_stats(current_agent_id)
	
	# Get paginated reviews list
	reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"agent": current_agent_id,
			"status": ["in", ["Submitted", "Published"]],
		},
		fields=[
			"name",
			"overall_rating",
			"agent_rating",
			"property_rating",
			"review_text",
			"creation",
			"customer",
			"guest_display_name",
			"property",
			"appointment",
		],
		order_by="creation desc",
		start=start,
		limit=page_size,
		ignore_permissions=True,
	)
	
	# Get total count for pagination
	total_count = rating_stats.get("total_reviews", 0)
	
	# Serialize reviews
	review_items = []
	for review in reviews:
		property_title = frappe.db.get_value("Property", review.get("property"), "title") if review.get("property") else None
		
		review_items.append({
			"id": review.get("name"),
			"overall_rating": _denormalize_rating(review.get("overall_rating")),
			"agent_rating": _denormalize_rating(review.get("agent_rating")),
			"property_rating": _denormalize_rating(review.get("property_rating")),
			"review_text": review.get("review_text") or "",
			"reviewer_name": _resolve_reviewer_name(
				review.get("customer"), review.get("guest_display_name")
			),
			"property_title": property_title,
			"appointment_id": review.get("appointment"),
			"created_at": review.get("creation"),
		})
	
	return {
		"agent_id": agent_id,
		"ratings": {
			"average_overall_rating": rating_stats.get("average_overall_rating", 0.0),
			"average_agent_rating": rating_stats.get("average_agent_rating", 0.0),
			"average_property_rating": rating_stats.get("average_property_rating", 0.0),
			"total_reviews": total_count,
		},
		"items": review_items,
		"page": page,
		"page_size": page_size,
		"total_items": total_count,
		"total_pages": (total_count + page_size - 1) // page_size if page_size else 0,
	}



def get_property_rating_stats(property_id: str) -> dict[str, Any]:
	"""Get rating statistics for a property"""
	# Get all submitted/published reviews for this property
	reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"property": property_id,
			"status": ["in", ["Submitted", "Published"]],
		},
		fields=[
			"overall_rating",
			"agent_rating",
			"property_rating",
			"review_text",
			"creation",
			"customer",
		],
		order_by="creation desc",
		limit=10,
		ignore_permissions=True,
	)
	
	if not reviews:
		return {
			"average_overall_rating": 0.0,
			"average_agent_rating": 0.0,
			"average_property_rating": 0.0,
			"total_reviews": 0,
			"recent_reviews": [],
		}
	
	# Calculate averages from all reviews
	all_reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"property": property_id,
			"status": ["in", ["Submitted", "Published"]],
		},
		fields=["overall_rating", "agent_rating", "property_rating"],
		ignore_permissions=True,
	)
	total_count = len(all_reviews)
	
	overall_sum = sum(float(r.get("overall_rating") or 0) for r in all_reviews)
	agent_sum = sum(float(r.get("agent_rating") or 0) for r in all_reviews)
	property_sum = sum(float(r.get("property_rating") or 0) for r in all_reviews)
	
	# Serialize recent reviews
	recent_reviews = []
	for review in reviews[:5]:
		customer_name = frappe.db.get_value("Customer", review.get("customer"), "full_name")
		recent_reviews.append({
			"overall_rating": _denormalize_rating(review.get("overall_rating")),
			"agent_rating": _denormalize_rating(review.get("agent_rating")),
			"property_rating": _denormalize_rating(review.get("property_rating")),
			"review_text": review.get("review_text") or "",
			"customer_name": customer_name,
			"created_at": review.get("creation"),
		})
	
	return {
		"average_overall_rating": round((overall_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"average_agent_rating": round((agent_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"average_property_rating": round((property_sum / total_count) * 5, 2) if total_count > 0 else 0.0,
		"total_reviews": total_count,
		"recent_reviews": recent_reviews,
	}


@frappe.whitelist(allow_guest=True)
def get_property_reviews(property_id: str) -> dict[str, Any]:
	"""
	Public API to get reviews for a property - no authentication required
	"""
	if not frappe.db.exists("Property", property_id):
		frappe.throw(_("Property not found."), frappe.DoesNotExistError)
	
	page = max(1, cint(frappe.form_dict.get("page") or 1))
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size
	
	rating_stats = get_property_rating_stats(property_id)
	
	reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"property": property_id,
			"status": ["in", ["Submitted", "Published"]],
		},
		fields=[
			"name",
			"overall_rating",
			"agent_rating",
			"property_rating",
			"review_text",
			"creation",
			"customer",
			"guest_display_name",
			"property",
			"appointment",
		],
		order_by="creation desc",
		start=start,
		limit=page_size,
		ignore_permissions=True,
	)
	
	total_count = rating_stats.get("total_reviews", 0)
	
	review_items = []
	for review in reviews:
		review_items.append({
			"id": review.get("name"),
			"overall_rating": _denormalize_rating(review.get("overall_rating")),
			"agent_rating": _denormalize_rating(review.get("agent_rating")),
			"property_rating": _denormalize_rating(review.get("property_rating")),
			"review_text": review.get("review_text") or "",
			"reviewer_name": _resolve_reviewer_name(
				review.get("customer"), review.get("guest_display_name")
			),
			"appointment_id": review.get("appointment"),
			"created_at": review.get("creation"),
		})
	
	return {
		"property_id": property_id,
		"ratings": {
			"average_overall_rating": rating_stats.get("average_overall_rating", 0.0),
			"average_agent_rating": rating_stats.get("average_agent_rating", 0.0),
			"average_property_rating": rating_stats.get("average_property_rating", 0.0),
			"total_reviews": total_count,
		},
		"items": review_items,
		"page": page,
		"page_size": page_size,
		"total_items": total_count,
		"total_pages": (total_count + page_size - 1) // page_size if page_size else 0,
	}


def _normalize_rating_input(value: Any) -> float:
	rating = float(value or 0)
	if rating < 0:
		return 0.0
	if rating > 1:
		rating = rating / 5
	return min(rating, 1.0)


def _denormalize_rating(value: Any) -> float:
	return float(value or 0) * 5 if value else 0.0
