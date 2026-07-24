import { agencyStore } from '@/stores/agency'
import { agentStore } from '@/stores/agent'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { isUnverifiedAgent as agentNeedsOnboarding } from '@/utils/agentOnboarding'
import { agencyNeedsDdaLicenseSync } from '@/utils/agencyOnboarding'

/**
 * Pending onboarding / verification / billing items for SaaS header + banner.
 */
export function useSaasPendingItems() {
  const agency = agencyStore()
  const { context: agencyContext } = storeToRefs(agency)
  const { agentResource } = agentStore()

  const items = computed(() => {
    void agencyContext.value?.onboarding_status
    void agencyContext.value?.verification_status
    void agencyContext.value?.requires_billing_activation
    void agentResource.data?.status

    const out = []
    if (agency.needsAgencyOnboarding()) {
      out.push({
        key: 'agency_onboarding',
        label: __('Agency onboarding'),
        detail: __('Complete company profile and billing.'),
        to: { name: 'Agency Onboarding' },
      })
    }
    if (agency.needsAgencyVerification()) {
      out.push({
        key: 'agency_verification',
        label: __('Agency verification'),
        detail: __('Review or update verification status.'),
        to: { name: 'Agency Verification' },
      })
    }
    const agentNeedsWork =
      Boolean(agentResource.data?.name) &&
      agentNeedsOnboarding(agentResource.data)
    if (agentNeedsWork && !agency.needsAgencyVerification() && !agency.needsAgencyOnboarding()) {
      out.push({
        key: 'agent_onboarding',
        label: __('Agent profile'),
        detail: __('Finish KYC and submit for verification.'),
        to: { name: 'Agent Onboarding' },
      })
    }
    if (agency.needsBillingActivation()) {
      out.push({
        key: 'billing_activation',
        label: __('Billing activation'),
        detail: __('Activate billing to continue.'),
        to: { name: 'Billing Activation' },
      })
    }
    if (agencyNeedsDdaLicenseSync(agencyContext.value)) {
      out.push({
        key: 'agency_dda_license',
        label: __('Agency license sync'),
        detail: __('Broker license pending DDA sync — some features may be limited.'),
      })
    }
    return out
  })

  return { items }
}
