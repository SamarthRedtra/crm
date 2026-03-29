<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Activate Billing') }}</h1>
      <p class="mt-1 text-p-sm text-ink-gray-5">
        {{ __('Your trial or onboarding phase has ended. Activate billing to continue using CRM.') }}
      </p>

      <div class="mt-5 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
        <div class="flex items-center justify-between gap-2">
          <span class="text-p-sm text-ink-gray-6">{{ __('Billing Status') }}</span>
          <Badge :label="billingStatusLabel" variant="subtle" :theme="billingTheme" />
        </div>
        <div class="mt-2 flex items-center justify-between gap-2">
          <span class="text-p-sm text-ink-gray-6">{{ __('Trial Status') }}</span>
          <Badge :label="trialStatusLabel" variant="subtle" :theme="trialTheme" />
        </div>
      </div>

      <div class="mt-5 flex flex-wrap gap-2">
        <Button variant="solid" :label="__('Set Up Billing Method')" :loading="setupLoading" @click="startSetup" />
        <Button variant="subtle" :label="__('Refresh')" :loading="refreshLoading" @click="refreshContext" />
        <Button v-if="isBillingActive" variant="ghost" :label="__('Go to Dashboard')" @click="router.push({ name: 'Home' })" />
      </div>

      <ErrorMessage class="mt-4" :message="errorMessage" />
    </div>
  </div>
</template>

<script setup>
import { agencyStore } from '@/stores/agency'
import { Badge, Button, ErrorMessage, call } from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { context, contextResource } = agencyStore()

const errorMessage = ref('')
const setupLoading = ref(false)
const refreshLoading = ref(false)

const billingStatus = computed(() => context.value.billing_status || 'Not Configured')
const trialStatus = computed(() => context.value.trial_status || 'Not Started')
const isBillingActive = computed(() => billingStatus.value === 'Active')

const billingStatusLabel = computed(() => billingStatus.value)
const trialStatusLabel = computed(() => trialStatus.value)

const billingTheme = computed(() => {
  if (billingStatus.value === 'Active') return 'green'
  if (billingStatus.value === 'Past Due') return 'red'
  return 'orange'
})

const trialTheme = computed(() => {
  if (trialStatus.value === 'Converted') return 'green'
  if (trialStatus.value === 'Expired') return 'red'
  if (trialStatus.value === 'Active' || trialStatus.value === 'Grace') return 'blue'
  return 'gray'
})

async function startSetup() {
  errorMessage.value = ''
  setupLoading.value = true
  try {
    const successUrl = `${window.location.origin}/crm/billing-activation?billing=success`
    const cancelUrl = `${window.location.origin}/crm/billing-activation?billing=cancel`
    const response = await call('crm.api.redtra.billing.create_billing_setup_session', {
      success_url: successUrl,
      cancel_url: cancelUrl,
    })
    if (response?.url) {
      window.location.href = response.url
      return
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    setupLoading.value = false
  }
}

async function refreshContext() {
  errorMessage.value = ''
  refreshLoading.value = true
  try {
    await contextResource.reload()
    if (isBillingActive.value) {
      router.push({ name: 'Home' })
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    refreshLoading.value = false
  }
}
</script>
