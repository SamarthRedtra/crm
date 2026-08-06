import frappe


_USER_MANAGEMENT_ROLES = ["System Manager", "Sales Manager", "Agency Admin", "Agency Manager"]


def _has_crm_wide_user_management_access() -> bool:
	roles = set(frappe.get_roles(frappe.session.user))
	return frappe.session.user == "Administrator" or bool(
		roles.intersection({"System Manager", "Sales Manager"})
	)


def _viewer_agency_for_user_management() -> str:
	agency = frappe.db.get_value("Agent", {"user": frappe.session.user}, "agency")
	if not agency:
		frappe.throw(frappe._("Your user is not linked to an agency."), frappe.PermissionError)
	return agency


def _assert_user_management_scope(user: str) -> None:
	"""Prevent agency managers from changing users outside their own agency."""
	if _has_crm_wide_user_management_access():
		return

	viewer_agency = _viewer_agency_for_user_management()
	target_agency = frappe.db.get_value("Agent", {"user": user}, "agency")
	if not target_agency or target_agency != viewer_agency:
		frappe.throw(frappe._("Not permitted to manage users outside your agency."), frappe.PermissionError)


@frappe.whitelist()
def get_existing_user_candidates():
	"""Return existing users eligible for the current user's Add Existing flow.

	Agency managers receive only Agent-linked users from their agency. CRM-wide
	managers keep the legacy all-user candidate list.
	"""
	frappe.only_for(_USER_MANAGEMENT_ROLES)

	filters = {"enabled": 1}
	if _has_crm_wide_user_management_access():
		return frappe.get_all(
			"User",
			filters=filters,
			fields=["name", "email", "full_name", "user_image"],
			order_by="full_name asc",
		)

	agency = _viewer_agency_for_user_management()
	user_names = frappe.get_all("Agent", filters={"agency": agency}, pluck="user")
	if not user_names:
		return []

	filters["name"] = ["in", user_names]
	return frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "email", "full_name", "user_image"],
		order_by="full_name asc",
	)


@frappe.whitelist()
def add_existing_users(users, role="Sales User"):
	"""
	Add existing users to the CRM by assigning them a role (Sales User or Sales Manager).
	:param users: List of user names to be added
	"""
	frappe.only_for(_USER_MANAGEMENT_ROLES)
	users = frappe.parse_json(users)

	for user in users:
		_assert_user_management_scope(user)
		add_user(user, role)


@frappe.whitelist()
def update_user_role(user, new_role):
	"""
	Update the role of the user to Sales Manager, Sales User, or System Manager.
	:param user: The name of the user
	:param new_role: The new role to assign (Sales Manager or Sales User)
	"""

	frappe.only_for(_USER_MANAGEMENT_ROLES)
	_assert_user_management_scope(user)

	if new_role not in ["System Manager", "Sales Manager", "Sales User", "Agency Admin", "Agency Manager"]:
		frappe.throw("Cannot assign this role")
	if not _has_crm_wide_user_management_access() and new_role != "Sales User":
		frappe.throw(frappe._("Agency managers can only grant Sales User access."), frappe.PermissionError)

	user_doc = frappe.get_doc("User", user)

	if new_role == "System Manager":
		user_doc.append_roles("System Manager", "Sales Manager", "Sales User")
		user_doc.set("block_modules", [])
	if new_role == "Sales Manager":
		user_doc.append_roles("Sales Manager", "Sales User")
		user_doc.remove_roles("System Manager")
	if new_role == "Agency Admin":
		user_doc.append_roles("Agency Admin", "Agency Manager", "Agent", "Sales User")
		user_doc.remove_roles("System Manager", "Sales Manager")
	if new_role == "Agency Manager":
		user_doc.append_roles("Agency Manager", "Agent", "Sales User")
		user_doc.remove_roles("System Manager", "Sales Manager", "Agency Admin")
	if new_role == "Sales User":
		user_doc.append_roles("Sales User")
		user_doc.remove_roles("Sales Manager", "System Manager", "Agency Admin", "Agency Manager")
		update_module_in_user(user_doc, "FCRM")

	user_doc.save(ignore_permissions=True)


def _sync_frappe_roles_from_agency_role(user: str, agency_role: str) -> None:
	"""Align User roles with Agent.agency_role (Agent / Manager / Admin team roles).

	Does not grant System Manager / Sales Manager (CRM-wide roles). Those stay unchanged unless removed explicitly elsewhere.
	"""
	ar = (agency_role or "Agent").strip()
	if ar not in {"Agent", "Manager", "Admin"}:
		frappe.throw(frappe._("Invalid agency role."))

	user_doc = frappe.get_doc("User", user)
	user_doc.flags.ignore_permissions = True

	if ar == "Admin":
		user_doc.add_roles("Agency Admin", "Agency Manager", "Agent", "Sales User")
	elif ar == "Manager":
		user_doc.add_roles("Agency Manager", "Agent", "Sales User")
		user_doc.remove_roles("Agency Admin")
	elif ar == "Agent":
		user_doc.add_roles("Agent", "Sales User")
		user_doc.remove_roles("Agency Admin", "Agency Manager")

	update_module_in_user(user_doc, "FCRM")
	user_doc.save(ignore_permissions=True)


@frappe.whitelist()
def update_agency_team_member_role(user, agency_role):
	"""Update Agent.agency_role (Agent / Manager / Admin) and sync CRM roles for that team member."""
	frappe.only_for(_USER_MANAGEMENT_ROLES)
	_assert_user_management_scope(user)

	ar = (agency_role or "").strip()
	if ar not in {"Agent", "Manager", "Admin"}:
		frappe.throw(frappe._("Invalid agency role."))

	session_roles = frappe.get_roles(frappe.session.user)
	elevated = frappe.session.user == "Administrator" or (
		"System Manager" in session_roles or "Sales Manager" in session_roles
	)

	agent_name = frappe.db.get_value("Agent", {"user": user}, "name")
	if not agent_name:
		frappe.throw(frappe._("User is not linked to an agency profile."))

	agent_doc = frappe.get_doc("Agent", agent_name)

	if not elevated:
		viewer_agency = frappe.db.get_value("Agent", {"user": frappe.session.user}, "agency")
		if not viewer_agency or agent_doc.agency != viewer_agency:
			frappe.throw(frappe._("Not permitted"), frappe.PermissionError)

	target_roles = frappe.get_roles(user)
	if "System Manager" in target_roles and not elevated:
		frappe.throw(frappe._("Cannot change agency role for this user."))

	if agent_doc.agency_role == "Admin" and ar != "Admin":
		other_admins = frappe.db.count(
			"Agent",
			filters={"agency": agent_doc.agency, "agency_role": "Admin", "name": ["!=", agent_doc.name]},
		)
		if other_admins < 1:
			frappe.throw(frappe._("The agency must keep at least one Admin."))

	agent_doc.agency_role = ar
	agent_doc.flags.ignore_permissions = True
	agent_doc.save()

	_sync_frappe_roles_from_agency_role(user, ar)


@frappe.whitelist()
def add_user(user, role):
	"""
	Add a user means adding role (Sales User or/and Sales Manager) to the user.
	:param user: The name of the user to be added
	:param role: The role to be assigned (Sales User or Sales Manager)
	"""
	update_user_role(user, role)


@frappe.whitelist()
def remove_user(user):
	"""
	Remove a user means removing Sales User & Sales Manager roles from the user.
	:param user: The name of the user to be removed
	"""
	frappe.only_for(_USER_MANAGEMENT_ROLES)
	_assert_user_management_scope(user)

	user_doc = frappe.get_doc("User", user)
	roles = [d.role for d in user_doc.roles]

	if "Sales User" in roles:
		user_doc.remove_roles("Sales User")
	if "Sales Manager" in roles:
		user_doc.remove_roles("Sales Manager")
	if "Agency Admin" in roles:
		user_doc.remove_roles("Agency Admin")
	if "Agency Manager" in roles:
		user_doc.remove_roles("Agency Manager")

	user_doc.save(ignore_permissions=True)
	frappe.msgprint(f"User {user} has been removed from CRM roles.")


def update_module_in_user(user, module):
	block_modules = frappe.get_all(
		"Module Def",
		fields=["name as module"],
		filters={"name": ["!=", module]},
	)

	if block_modules:
		user.set("block_modules", block_modules)
