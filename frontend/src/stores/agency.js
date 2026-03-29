import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { computed } from 'vue'

export const agencyStore = defineStore('crm-agency', () => {
  const contextResource = createResource({
    url: 'crm.api.redtra.billing.get_session_agency_context',
    cache: 'AgencyContext',
    auto: true,
  })

  const context = computed(() => contextResource.data || {})

  function hasAgency() {
    return Boolean(context.value.agency)
  }

  function isInternalManager() {
    return Boolean(context.value.is_internal_manager)
  }

  function isAgencyAdmin() {
    return Boolean(context.value.can_manage_billing)
  }

  function isAgencyManager() {
    return Boolean(context.value.can_manage_team)
  }

  function needsAgencyOnboarding() {
    return Boolean(
      hasAgency() &&
        isAgencyAdmin() &&
        (context.value.verification_status || 'Verified') === 'Verified' &&
        context.value.onboarding_status &&
        context.value.onboarding_status !== 'Completed',
    )
  }

  function needsAgencyVerification() {
    if (!hasAgency() || !isAgencyAdmin()) return false
    const status = context.value.verification_status || 'Verified'
    return status === 'Pending Verification' || status === 'Rejected'
  }

  function needsBillingActivation() {
    return Boolean(hasAgency() && isAgencyAdmin() && context.value.requires_billing_activation)
  }

  function hasTrialExpired() {
    return Boolean(
      hasAgency() &&
        isAgencyAdmin() &&
        ['Expired'].includes(context.value.trial_status),
    )
  }

  return {
    contextResource,
    context,
    hasAgency,
    isInternalManager,
    isAgencyAdmin,
    isAgencyManager,
    needsAgencyOnboarding,
    needsAgencyVerification,
    needsBillingActivation,
    hasTrialExpired,
  }
})
