import { call } from 'frappe-ui'

/**
 * After 3DS / bank redirect, Stripe sends the user back with setup_intent + redirect_status.
 * Call this on pages that open StripeSetupPaymentModal so the CRM doctype stays in sync.
 */
export async function finalizeStripeSetupReturn({ route, router, agencyId, onSuccess }) {
  const q = route.query
  if (q.redirect_status !== 'succeeded' || !q.setup_intent) {
    return false
  }
  if (q.stripe_setup !== '1') {
    return false
  }
  try {
    await call('crm.api.redtra.billing.complete_stripe_setup_intent', {
      setup_intent_id: q.setup_intent,
      agency_id: agencyId || undefined,
    })
    if (onSuccess) {
      await onSuccess()
    }
    const nextQ = { ...q }
    delete nextQ.setup_intent
    delete nextQ.setup_intent_client_secret
    delete nextQ.redirect_status
    delete nextQ.stripe_setup
    await router.replace({ path: route.path, query: nextQ })
    return true
  } catch {
    return false
  }
}
