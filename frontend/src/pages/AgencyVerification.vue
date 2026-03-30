<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Agency Verification') }}</h1>
      <p class="mt-1 text-p-sm text-ink-gray-5">
        {{
          __(
            'Your company (agency) registration is reviewed by operations. This is separate from your personal agent profile and KYC documents.',
          )
        }}
      </p>

      <div v-if="contextResource.loading && !contextResource.data" class="mt-8 flex justify-center py-6">
        <LoadingIndicator class="size-8" />
      </div>

      <template v-else>
        <div class="mt-5 rounded-lg border border-outline-blue-1 bg-surface-blue-1 p-4 text-p-sm text-ink-gray-7">
          <p class="font-medium text-ink-gray-8">{{ __('Where to manage documents & status') }}</p>
          <ul class="mt-2 list-inside list-disc space-y-1">
            <li>
              {{
                __(
                  'Agent KYC documents and your verification status: open Agent Onboarding (personal profile).',
                )
              }}
            </li>
            <li>
              {{
                __(
                  'Agency company details (BRN, contacts): use Agency Onboarding after agency verification is approved.',
                )
              }}
            </li>
          </ul>
          <div class="mt-3 flex flex-wrap gap-2">
            <Button variant="outline" :label="__('Open Agent Onboarding')" @click="goAgentOnboarding" />
            <Button
              v-if="isVerified"
              variant="subtle"
              :label="__('Open Agency Onboarding')"
              @click="router.push({ name: 'Agency Onboarding' })"
            />
          </div>
        </div>

        <div class="mt-5 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-p-sm font-medium text-ink-gray-8">{{ __('Billing & subscription') }}</p>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{
              __(
                'Charges follow agent levels and optional add-ons (you choose those in Settings → Agency Profile once you have CRM access). Payment method and Stripe are completed in Agency Onboarding when billing is enabled.',
              )
            }}
          </p>
          <div class="mt-3 flex flex-wrap gap-2">
            <Badge
              :label="__('Payment mode: {0}', [context?.payment_mode || 'two_step'])"
              variant="subtle"
              theme="gray"
            />
            <Badge
              v-if="context?.trial_status"
              :label="__('Trial: {0}', [context.trial_status])"
              variant="subtle"
              theme="blue"
            />
            <Badge
              v-if="context?.is_on_trial"
              :label="__('On trial')"
              variant="subtle"
              theme="green"
            />
            <Badge
              v-if="context?.requires_billing_activation"
              :label="__('Activate payment method')"
              variant="subtle"
              theme="orange"
            />
          </div>
          <p v-if="context?.trial_end_date" class="mt-2 text-p-xs text-ink-gray-5">
            {{ __('Trial end: {0}', [context.trial_end_date]) }}
          </p>
        </div>

        <div class="mt-6 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
          <div class="flex items-center justify-between gap-2">
            <span class="text-p-sm text-ink-gray-6">{{ __('Agency verification status') }}</span>
            <Badge :label="verificationLabel" variant="subtle" :theme="verificationTheme" />
          </div>

          <p v-if="agencyName" class="mt-2 text-p-sm text-ink-gray-6">
            <span class="font-medium text-ink-gray-7">{{ __('Agency:') }}</span> {{ agencyName }}
          </p>

          <p v-if="verificationNotes" class="mt-3 text-p-sm text-ink-gray-7">
            <span class="font-medium">{{ __('Ops notes:') }}</span> {{ verificationNotes }}
          </p>

          <p v-if="isRejected" class="mt-3 text-p-sm text-red-600">
            {{ __('Please update agency details and use Request Re-Verification when ready.') }}
          </p>

          <p v-else-if="isPending" class="mt-3 text-p-sm text-ink-gray-6">
            {{ __('Your agency registration is under review. We will unlock the next steps when it is approved.') }}
          </p>
        </div>

        <div class="mt-5 flex flex-wrap gap-2">
          <Button variant="subtle" :label="__('Refresh Status')" :loading="loading" @click="refreshContext" />
          <Button
            v-if="isRejected"
            variant="outline"
            :label="resubmitLoading ? __('Submitting...') : __('Request Re-Verification')"
            :loading="resubmitLoading"
            @click="requestReverification"
          />
          <Button
            v-if="isVerified"
            variant="solid"
            :label="__('Continue to Agency Onboarding')"
            @click="router.push({ name: 'Agency Onboarding' })"
          />
        </div>
      </template>

      <ErrorMessage class="mt-4" :message="errorMessage" />
    </div>
  </div>
</template>

<script setup>
import { agencyStore } from '@/stores/agency'
import { Badge, Button, ErrorMessage, LoadingIndicator, call } from 'frappe-ui'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const agency = agencyStore()
const { context } = storeToRefs(agency)
const { contextResource } = agency

const errorMessage = ref('')
const loading = ref(false)
const resubmitLoading = ref(false)

const verificationStatus = computed(() => context.value?.verification_status || 'Pending Verification')
const verificationNotes = computed(() => context.value?.verification_notes || '')
const agencyName = computed(() => context.value?.agency_name || context.value?.agency || '')

const isVerified = computed(() => verificationStatus.value === 'Verified')
const isPending = computed(() => verificationStatus.value === 'Pending Verification')
const isRejected = computed(() => verificationStatus.value === 'Rejected')

const verificationTheme = computed(() => {
  if (isVerified.value) return 'green'
  if (isRejected.value) return 'red'
  return 'orange'
})

const verificationLabel = computed(() => verificationStatus.value)

function goAgentOnboarding() {
  router.push({ name: 'Agent Onboarding' })
}

async function refreshContext() {
  errorMessage.value = ''
  loading.value = true
  try {
    await contextResource.reload()
    if (isVerified.value) {
      router.push({ name: 'Agency Onboarding' })
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    loading.value = false
  }
}

async function requestReverification() {
  errorMessage.value = ''
  resubmitLoading.value = true
  try {
    await call('crm.api.redtra.billing.request_agency_reverification')
    await refreshContext()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    resubmitLoading.value = false
  }
}
</script>
