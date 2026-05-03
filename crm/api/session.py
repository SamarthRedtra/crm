import frappe


@frappe.whitelist()
def get_users():
	users = frappe.qb.get_query(
		"User",
		fields=[
			"name",
			"email",
			"enabled",
			"user_image",
			"first_name",
			"last_name",
			"full_name",
			"user_type",
		],
		order_by="full_name asc",
		distinct=True,
	).run(as_dict=1)

	names = [u.name for u in users]
	agent_rows = (
		frappe.get_all(
			"Agent",
			filters={"user": ["in", names]},
			fields=["user", "agency", "agency_role"],
		)
		if names
		else []
	)
	agent_by_user = {row.user: row for row in agent_rows}

	for user in users:
		if frappe.session.user == user.name:
			user.session_user = True

		user.roles = frappe.get_roles(user.name)

		user.role = ""

		if "System Manager" in user.roles:
			user.role = "System Manager"
		elif "Sales Manager" in user.roles:
			user.role = "Sales Manager"
		elif "Agency Admin" in user.roles:
			user.role = "Agency Admin"
		elif "Agency Manager" in user.roles:
			user.role = "Agency Manager"
		elif "Sales User" in user.roles:
			user.role = "Sales User"
		elif "Guest" in user.roles:
			user.role = "Guest"

		user.is_telephony_agent = frappe.db.exists("CRM Telephony Agent", {"user": user.name})

		agent_row = agent_by_user.get(user.name)
		user.agent_agency = agent_row.agency if agent_row else None
		user.agency_role = agent_row.agency_role if agent_row else None

	crm_users = []

	# crm users are users with role Sales User or Sales Manager
	for user in users:
		if any(role in user.roles for role in ["Sales User", "Sales Manager", "Agency Admin", "Agency Manager"]):
			crm_users.append(user)

	session_user = frappe.session.user
	session_roles = frappe.get_roles(session_user)

	def _crm_users_full_scope() -> bool:
		if session_user == "Administrator":
			return True
		if "System Manager" in session_roles or "Sales Manager" in session_roles:
			return True
		return False

	viewer_agency = None
	if not _crm_users_full_scope() and (
		"Agency Admin" in session_roles or "Agency Manager" in session_roles
	):
		viewer_agency = frappe.db.get_value("Agent", {"user": session_user}, "agency")
		if viewer_agency:
			crm_users = [u for u in crm_users if u.get("agent_agency") == viewer_agency]
		else:
			crm_users = []

	viewer_meta = {
		"users_scope": "all" if _crm_users_full_scope() else "agency",
		"agency": viewer_agency,
	}

	return users, crm_users, viewer_meta


@frappe.whitelist()
def get_organizations():
	organizations = frappe.qb.get_query(
		"CRM Organization",
		fields=["*"],
		order_by="name asc",
		distinct=True,
	).run(as_dict=1)

	return organizations
