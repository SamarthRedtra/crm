/**
 * CRM Manager dashboard access — keep in sync with `crm.utils.can_access_crm_dashboard`
 * and Property rules in `crm.api.redtra.permissions` (agency Admin/Manager).
 */

/** Same as `has_agency_wide_property_access`: agency set + Admin/Manager on Agent. */
export function hasAgencyWidePropertyAccess(agentDoc) {
  const ar = agentDoc?.agency_role
  return Boolean(agentDoc?.agency && (ar === 'Admin' || ar === 'Manager'))
}

export function userCanAccessDashboard(sessionUser, userDoc, agentDoc) {
  if (!sessionUser) return false
  const roles = userDoc?.roles || []
  if (roles.includes('System Manager') || roles.includes('Sales Manager')) {
    return true
  }
  // Agency Admin/Manager (matches Property + dashboard API)
  const ar = agentDoc?.agency_role
  return ar === 'Admin' || ar === 'Manager'
}
