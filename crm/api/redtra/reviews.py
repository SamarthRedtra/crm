from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from . import utils


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
		review_doc.overall_rating = data.get("overall_rating", 0)
	if "agent_rating" in data:
		review_doc.agent_rating = data.get("agent_rating", 0)
	if "property_rating" in data:
		review_doc.property_rating = data.get("property_rating", 0)
	if "review_text" in data:
		review_doc.review_text = data.get("review_text", "")
	
	# Set status to Submitted
	review_doc.status = "Submitted"
	
	review_doc.save(ignore_permissions=True)
	frappe.db.commit()
	
	return serialize_review(review_doc.name)
	return serialize_review(review_doc.name)


@frappe.whitelist()
@utils.require_jwt()
def submit_agent_review(agent_id: str) -> dict[str, Any]:
	"""Submit a review for an agent (without appointment)"""
	return _submit_general_review(agent_id=agent_id)


@frappe.whitelist()
@utils.require_jwt()
def submit_property_review(property_id: str) -> dict[str, Any]:
	"""Submit a review for a property (without appointment)"""
	return _submit_general_review(property_id=property_id)


def _submit_general_review(agent_id: str | None = None, property_id: str | None = None) -> dict[str, Any]:
	data = utils.get_request_json()
	current_user = utils.get_current_user()
	customer = utils.get_customer_by_user(current_user)
	
	if not customer:
		frappe.throw(_("Customer profile is required to submit reviews."), frappe.PermissionError)

	filters = {"customer": customer.name}
	if agent_id:
		filters["agent"] = agent_id
		filters["appointment"] = ["is", "not set"] # Explicitly filter NULL
		# Ensure agent exists
		if not frappe.db.exists("Agent", agent_id):
			frappe.throw(_("Agent not found."), frappe.DoesNotExistError)
	elif property_id:
		filters["property"] = property_id
		filters["appointment"] = ["is", "not set"]
		# Ensure property exists
		if not frappe.db.exists("Property", property_id):
			frappe.throw(_("Property not found."), frappe.DoesNotExistError)
	else:
		frappe.throw(_("Target is required."), frappe.ValidationError)

	# Check for existing review from this customer for this target
	# We allow one general review per customer per target
	existing_review = frappe.db.get_value("Review and Rating", filters, "name")

	if existing_review:
		review_doc = frappe.get_doc("Review and Rating", existing_review)
	else:
		review_doc = frappe.new_doc("Review and Rating")
		review_doc.customer = customer.name
		if agent_id:
			review_doc.agent = agent_id
		if property_id:
			review_doc.property = property_id
		review_doc.status = "Draft"

	if "overall_rating" in data:
		review_doc.overall_rating = data.get("overall_rating", 0)
	if "agent_rating" in data:
		review_doc.agent_rating = data.get("agent_rating", 0)
	if "property_rating" in data:
		review_doc.property_rating = data.get("property_rating", 0)
	if "review_text" in data:
		review_doc.review_text = data.get("review_text", "")

	review_doc.status = "Submitted"
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
	
	customer_name = frappe.db.get_value("Customer", review_doc.customer, "full_name")
	
	return {
		"id": review_doc.name,
		"appointment_id": review_doc.appointment,
		"agent_id": review_doc.agent,
		"property_id": review_doc.property,
		"customer_id": review_doc.customer,
		"reviewer_name": customer_name,
		"overall_rating": float(review_doc.overall_rating or 0) if review_doc.overall_rating else 0.0,
		"agent_rating": float(review_doc.agent_rating or 0) if review_doc.agent_rating else 0.0,
		"property_rating": float(review_doc.property_rating or 0) if review_doc.property_rating else 0.0,
		"review_text": review_doc.review_text or "",
		"status": review_doc.status,
		"submitted_at": review_doc.submitted_at,
		"created_at": review_doc.creation,
	}


def get_agent_rating_stats(agent_id: str) -> dict[str, Any]:
	"""Get rating statistics for an agent"""
	# Get all submitted/published reviews for this agent
	reviews = frappe.get_all(
		"Review and Rating",
		filters={
			"agent": agent_id,
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
		limit=10,  # Get recent reviews for display
	)
	
	if not reviews:
		return {
			"average_overall_rating": 0.0,
			"average_agent_rating": 0.0,
			"average_property_rating": 0.0,
			"total_reviews": 0,
			"recent_reviews": [],
		}
	
	# Calculate averages
	total_count = len(reviews)
	overall_sum = sum(float(r.get("overall_rating") or 0) for r in reviews)
	agent_sum = sum(float(r.get("agent_rating") or 0) for r in reviews)
	property_sum = sum(float(r.get("property_rating") or 0) for r in reviews)
	
	# Get all reviews for accurate averages (not just recent 10)
	all_reviews_count = frappe.db.count(
		"Review and Rating",
		filters={
			"agent": agent_id,
			"status": ["in", ["Submitted", "Published"]],
		}
	)
	
	if all_reviews_count > total_count:
		# Need to calculate from all reviews, not just recent 10
		all_reviews = frappe.get_all(
			"Review and Rating",
			filters={
				"agent": agent_id,
				"status": ["in", ["Submitted", "Published"]],
			},
			fields=["overall_rating", "agent_rating", "property_rating"],
		)
		total_count = len(all_reviews)
		overall_sum = sum(float(r.get("overall_rating") or 0) for r in all_reviews)
		agent_sum = sum(float(r.get("agent_rating") or 0) for r in all_reviews)
		property_sum = sum(float(r.get("property_rating") or 0) for r in all_reviews)
	
	# Serialize recent reviews
	recent_reviews = []
	for review in reviews[:5]:  # Show only 5 most recent in detail
		customer_name = frappe.db.get_value("Customer", review.get("customer"), "full_name")
		recent_reviews.append({
			"overall_rating": float(review.get("overall_rating") or 0),
			"agent_rating": float(review.get("agent_rating") or 0),
			"property_rating": float(review.get("property_rating") or 0),
			"review_text": review.get("review_text") or "",
			"reviewer_name": customer_name,
			"created_at": review.get("creation"),
		})
	
	return {
		"average_overall_rating": round(overall_sum / total_count, 2) if total_count > 0 else 0.0,
		"average_agent_rating": round(agent_sum / total_count, 2) if total_count > 0 else 0.0,
		"average_property_rating": round(property_sum / total_count, 2) if total_count > 0 else 0.0,
		"total_reviews": total_count,
		"recent_reviews": recent_reviews,
	}


@frappe.whitelist(allow_guest=True)
def get_agent_reviews(agent_id: str) -> dict[str, Any]:
	"""
	Public API to get reviews for an agent - no authentication required
	
	Returns paginated list of reviews with rating statistics.
	"""
	# Verify agent exists
	if not frappe.db.exists("Agent", agent_id):
		frappe.throw(_("Agent not found."), frappe.DoesNotExistError)
	
	# Get pagination parameters
	page = max(1, cint(frappe.form_dict.get("page") or 1))
	page_size = cint(frappe.form_dict.get("page_size") or 20)
	page_size = max(1, min(page_size, 100))
	start = (page - 1) * page_size
	
	# Get rating statistics (includes recent reviews)
	rating_stats = get_agent_rating_stats(agent_id)
	
	# Get paginated reviews list
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
			"property",
			"appointment",
		],
		order_by="creation desc",
		start=start,
		limit=page_size,
	)
	
	# Get total count for pagination
	total_count = rating_stats.get("total_reviews", 0)
	
	# Serialize reviews
	review_items = []
	for review in reviews:
		customer_name = frappe.db.get_value("Customer", review.get("customer"), "full_name")
		property_title = frappe.db.get_value("Property", review.get("property"), "title") if review.get("property") else None
		
		review_items.append({
			"id": review.get("name"),
			"overall_rating": float(review.get("overall_rating") or 0) if review.get("overall_rating") else 0.0,
			"agent_rating": float(review.get("agent_rating") or 0) if review.get("agent_rating") else 0.0,
			"property_rating": float(review.get("property_rating") or 0) if review.get("property_rating") else 0.0,
			"review_text": review.get("review_text") or "",
			"reviewer_name": customer_name,
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
			"overall_rating": float(review.get("overall_rating") or 0),
			"agent_rating": float(review.get("agent_rating") or 0),
			"property_rating": float(review.get("property_rating") or 0),
			"review_text": review.get("review_text") or "",
			"customer_name": customer_name,
			"created_at": review.get("creation"),
		})
	
	return {
		"average_overall_rating": round(overall_sum / total_count, 2) if total_count > 0 else 0.0,
		"average_agent_rating": round(agent_sum / total_count, 2) if total_count > 0 else 0.0,
		"average_property_rating": round(property_sum / total_count, 2) if total_count > 0 else 0.0,
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
			"property",
			"appointment",
		],
		order_by="creation desc",
		start=start,
		limit=page_size,
	)
	
	total_count = rating_stats.get("total_reviews", 0)
	
	review_items = []
	for review in reviews:
		customer_name = frappe.db.get_value("Customer", review.get("customer"), "full_name")
		
		review_items.append({
			"id": review.get("name"),
			"overall_rating": float(review.get("overall_rating") or 0) if review.get("overall_rating") else 0.0,
			"agent_rating": float(review.get("agent_rating") or 0) if review.get("agent_rating") else 0.0,
			"property_rating": float(review.get("property_rating") or 0) if review.get("property_rating") else 0.0,
			"review_text": review.get("review_text") or "",
			"reviewer_name": customer_name,
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
