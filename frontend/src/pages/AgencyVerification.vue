<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Agency Verification') }}</h1>
      <p class="mt-1 text-p-sm text-ink-gray-5">
        {{ __('Your agency access is controlled by verification status before full CRM activation.') }}
      </p>

      <div class="mt-6 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4">
        <div class="flex items-center justify-between gap-2">
          <span class="text-p-sm text-ink-gray-6">{{ __('Current Status') }}</span>
          <Badge
            :label="verificationLabel"
            variant="subtle"
            :theme="verificationTheme"
          />
        </div>

        <p v-if="verificationNotes" class="mt-3 text-p-sm text-ink-gray-7">
          <span class="font-medium">{{ __('Ops notes:') }}</span> {{ verificationNotes }}
        </p>

        <p v-if="isRejected" class="mt-3 text-p-sm text-red-600">
          {{ __('Please update agency details and re-submit onboarding for another review cycle.') }}
        </p>

        <p v-else-if="isPending" class="mt-3 text-p-sm text-ink-gray-6">
          {{ __('Your registration is under review. We will unlock onboarding once verification is approved.') }}
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
          :label="__('Continue to Onboarding')"
          @click="router.push({ name: 'Agency Onboarding' })"
        />
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
const loading = ref(false)
const resubmitLoading = ref(false)

const verificationStatus = computed(() => context.value.verification_status || 'Pending Verification')
const verificationNotes = computed(() => context.value.verification_notes || '')

const isVerified = computed(() => verificationStatus.value === 'Verified')
const isPending = computed(() => verificationStatus.value === 'Pending Verification')
const isRejected = computed(() => verificationStatus.value === 'Rejected')

const verificationTheme = computed(() => {
  if (isVerified.value) return 'green'
  if (isRejected.value) return 'red'
  return 'orange'
})

const verificationLabel = computed(() => verificationStatus.value)

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
