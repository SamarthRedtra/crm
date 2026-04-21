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
        <Button variant="solid" :label="__('Set Up Billing Method')" @click="startSetup" />
        <Button variant="subtle" :label="__('Refresh')" :loading="refreshLoading" @click="refreshContext" />
        <Button v-if="isBillingActive" variant="ghost" :label="__('Go to Dashboard')" @click="router.push({ name: 'Home' })" />
      </div>

      <StripeSetupPaymentModal
        v-model="showStripeModal"
        :agency-id="context?.agency"
        intent="billing_setup"
        return-path="/crm/billing-activation"
        @success="onStripeCardSaved"
      />

      <ErrorMessage class="mt-4" :message="errorMessage" />
    </div>
  </div>
</template>

<script setup>
import StripeSetupPaymentModal from '@/components/Billing/StripeSetupPaymentModal.vue'
import { finalizeStripeSetupReturn } from '@/composables/stripeSetupReturn'
import { agencyStore } from '@/stores/agency'
import { Badge, Button, ErrorMessage, toast } from 'frappe-ui'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const agency = agencyStore()
const { context } = storeToRefs(agency)
const { contextResource } = agency

const errorMessage = ref('')
const showStripeModal = ref(false)
const refreshLoading = ref(false)

const billingStatus = computed(() => context.value?.billing_status || 'Not Configured')
const trialStatus = computed(() => context.value?.trial_status || 'Not Started')
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

async function onStripeCardSaved() {
  toast.success(__('Card saved successfully'))
  await contextResource.reload()
  if (isBillingActive.value) {
    router.push({ name: 'Home' })
  }
}

async function startSetup() {
  errorMessage.value = ''
  showStripeModal.value = true
}

watch(
  () => [route.fullPath, context.value?.agency],
  async () => {
    if (!context.value?.agency) return
    await finalizeStripeSetupReturn({
      route,
      router,
      agencyId: context.value.agency,
      onSuccess: onStripeCardSaved,
    })
  },
  { immediate: true },
)

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
