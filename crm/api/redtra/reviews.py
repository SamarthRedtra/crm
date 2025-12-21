from __future__ import annotations

from typing import Any

import frappe
from frappe import _

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
	
	return {
		"id": review_doc.name,
		"appointment_id": review_doc.appointment,
		"agent_id": review_doc.agent,
		"property_id": review_doc.property,
		"customer_id": review_doc.customer,
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
