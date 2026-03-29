<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-4xl rounded-xl border border-outline-gray-2 bg-surface-white shadow-sm">
      <div class="border-b border-outline-gray-2 px-8 py-6">
        <div class="flex items-center gap-3">
          <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-surface-blue-1">
            <FeatherIcon name="building" class="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 class="text-xl font-semibold text-ink-gray-9">
              {{ __('Agency Onboarding') }}
            </h1>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('Complete your agency profile and billing setup before entering the CRM.') }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="management.loading" class="flex min-h-[420px] items-center justify-center">
        <LoadingIndicator class="size-8" />
      </div>

      <div v-else class="px-8 py-6">
        <div
          v-if="route.query.billing === 'success'"
          class="mb-5 rounded-lg border border-outline-green-1 bg-surface-green-1 px-4 py-3 text-p-sm text-green-700"
        >
          {{ __('Stripe billing setup completed successfully.') }}
        </div>
        <div
          v-else-if="route.query.billing === 'cancel'"
          class="mb-5 rounded-lg border border-outline-orange-1 bg-surface-yellow-1 px-4 py-3 text-p-sm text-yellow-700"
        >
          {{ __('Billing setup was cancelled. You can retry from the final step.') }}
        </div>

        <div v-if="!management.data?.agency" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5">
          <p class="text-p-sm text-ink-gray-6">
            {{ __('No agency is linked to your user yet.') }}
          </p>
        </div>

        <template v-else>
          <div class="mb-6 flex items-center gap-3">
            <template v-for="(step, index) in steps" :key="step.id">
              <div class="flex items-center gap-3">
                <div
                  class="flex h-7 w-7 items-center justify-center rounded-full text-p-xs font-semibold"
                  :class="index <= activeStep ? 'bg-blue-600 text-white' : 'bg-surface-gray-2 text-ink-gray-4'"
                >
                  {{ index + 1 }}
                </div>
                <span
                  class="text-p-sm font-medium"
                  :class="index === activeStep ? 'text-blue-600' : 'text-ink-gray-5'"
                >
                  {{ step.label }}
                </span>
              </div>
              <div
                v-if="index < steps.length - 1"
                class="h-px flex-1"
                :class="index < activeStep ? 'bg-blue-400' : 'bg-outline-gray-2'"
              />
            </template>
          </div>

          <div v-show="activeStep === 0" class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Agency Name') }}</label>
              <input v-model="form.agency_name" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Email') }}</label>
              <input v-model="form.email" type="email" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Phone') }}</label>
              <PhoneInput v-model="form.phone" :national-placeholder="__('50 000 0000')" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Website') }}</label>
              <input v-model="form.website" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('BRN ID') }}</label>
              <input v-model="form.brn_id" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Description') }}</label>
              <textarea v-model="form.description" rows="4" :class="inputClass"></textarea>
            </div>
          </div>

          <div v-show="activeStep === 1" class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Contact Name') }}</label>
              <input v-model="form.billing_contact_name" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Email') }}</label>
              <input v-model="form.billing_email" type="email" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Currency') }}</label>
              <Link
                class="form-control"
                :value="form.billing_currency"
                doctype="Currency"
                @change="(value) => (form.billing_currency = value)"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Start Date') }}</label>
              <input v-model="form.billing_start_date" type="date" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Address Line 1') }}</label>
              <input v-model="form.address_line1" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Address Line 2') }}</label>
              <input v-model="form.address_line2" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('City') }}</label>
              <input v-model="form.city" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('State') }}</label>
              <input v-model="form.state" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Country') }}</label>
              <input v-model="form.country" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('PIN Code') }}</label>
              <input v-model="form.pincode" :class="inputClass" />
            </div>
          </div>

          <div v-show="activeStep === 2" class="flex flex-col gap-4">
            <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5">
              <div class="flex items-start gap-3">
                <FeatherIcon name="credit-card" class="mt-0.5 h-4 w-4 text-ink-gray-5" />
                <div>
                  <p class="text-p-base font-medium text-ink-gray-8">
                    {{ __('Stripe Billing') }}
                  </p>
                  <p class="mt-1 text-p-sm text-ink-gray-5">
                    {{
                      management.data.stripe_enabled
                        ? __('Connect a card if you want monthly invoices to be paid through Stripe.')
                        : __('Stripe keys are not configured yet. You can still complete onboarding and configure billing later.')
                    }}
                  </p>
                </div>
              </div>

              <div class="mt-4 flex flex-wrap items-center gap-3">
                <Badge
                  :label="management.data.agency.billing_status || __('Not Configured')"
                  variant="subtle"
                  :theme="billingTheme(management.data.agency.billing_status)"
                />
                <Badge
                  :label="management.data.agency.onboarding_status || __('Not Started')"
                  variant="subtle"
                  theme="blue"
                />
                <Badge
                  :label="__('Mode: {0}', [management.data.payment_mode || 'two_step'])"
                  variant="subtle"
                  theme="gray"
                />
                <Badge
                  v-if="management.data.trial_config?.enabled"
                  :label="__('Trial: {0} days', [management.data.trial_config?.trial_days || 30])"
                  variant="subtle"
                  theme="blue"
                />
              </div>

              <div class="mt-4 flex flex-wrap gap-2">
                <Button
                  v-if="management.data.stripe_enabled"
                  variant="solid"
                  :label="__('Set Up Billing Method')"
                  :loading="setupLoading"
                  @click="startSetup"
                />
                <Button
                  variant="subtle"
                  :label="__('Refresh Status')"
                  @click="management.reload()"
                />
              </div>
            </div>
          </div>

          <div class="mt-6 flex items-center justify-between gap-3 border-t border-outline-gray-2 pt-5">
            <Button
              variant="subtle"
              :label="__('Back')"
              :disabled="activeStep === 0"
              @click="activeStep = Math.max(0, activeStep - 1)"
            />
            <div class="flex items-center gap-2">
              <Button
                v-if="activeStep < 2"
                variant="solid"
                :label="saveLoading ? __('Saving…') : __('Save & Continue')"
                :loading="saveLoading"
                @click="saveAndContinue"
              />
              <Button
                v-else
                variant="solid"
                :label="completeLoading ? __('Completing…') : __('Complete Onboarding')"
                :loading="completeLoading"
                @click="completeOnboarding"
              />
            </div>
          </div>
        </template>

        <ErrorMessage :message="errorMessage" />
      </div>
    </div>
  </div>
</template>

<script setup>
import PhoneInput from '@/components/PhoneInput.vue'
import Link from '@/components/Controls/Link.vue'
import { agencyStore } from '@/stores/agency'
import {
  Badge,
  Button,
  ErrorMessage,
  FeatherIcon,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { contextResource } = agencyStore()

const steps = [
  { id: 'profile', label: __('Agency Profile') },
  { id: 'billing', label: __('Billing Details') },
  { id: 'finish', label: __('Finish') },
]

const inputClass =
  'w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100'

const activeStep = ref(0)
const saveLoading = ref(false)
const setupLoading = ref(false)
const completeLoading = ref(false)
const errorMessage = ref('')

const form = reactive({
  agency_name: '',
  email: '',
  phone: '',
  website: '',
  brn_id: '',
  description: '',
  billing_contact_name: '',
  billing_email: '',
  billing_currency: '',
  billing_start_date: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  country: '',
  pincode: '',
})

function applyData(data) {
  const agency = data?.agency || {}
  Object.assign(form, {
    agency_name: agency.agency_name || '',
    email: agency.email || '',
    phone: agency.phone || '',
    website: agency.website || '',
    brn_id: agency.brn_id || '',
    description: agency.description || '',
    billing_contact_name: agency.billing_contact_name || '',
    billing_email: agency.billing_email || '',
    billing_currency: agency.billing_currency || '',
    billing_start_date: agency.billing_start_date || '',
    address_line1: agency.address_line1 || '',
    address_line2: agency.address_line2 || '',
    city: agency.city || '',
    state: agency.state || '',
    country: agency.country || '',
    pincode: agency.pincode || '',
  })
}

const management = createResource({
  url: 'crm.api.redtra.billing.get_agency_management_data',
  auto: true,
  onSuccess(data) {
    errorMessage.value = ''
    applyData(data)
  },
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

async function persistProfile() {
  await call('crm.api.redtra.billing.update_current_agency_profile', {
    agency_id: management.data?.agency?.name,
    data: JSON.stringify(form),
  })
  await management.reload()
  contextResource.reload()
}

async function saveAndContinue() {
  saveLoading.value = true
  errorMessage.value = ''
  try {
    await persistProfile()
    activeStep.value = Math.min(steps.length - 1, activeStep.value + 1)
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    saveLoading.value = false
  }
}

async function startSetup() {
  if (!management.data?.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  setupLoading.value = true
  errorMessage.value = ''
  try {
    await persistProfile()
    const successUrl = `${window.location.origin}/crm/agency-onboarding?billing=success`
    const cancelUrl = `${window.location.origin}/crm/agency-onboarding?billing=cancel`
    const response = await call('crm.api.redtra.billing.create_billing_setup_session', {
      agency_id: management.data?.agency?.name,
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

async function completeOnboarding() {
  completeLoading.value = true
  errorMessage.value = ''
  try {
    await persistProfile()
    await call('crm.api.redtra.billing.complete_agency_onboarding', {
      agency_id: management.data?.agency?.name,
    })
    toast.success(__('Agency onboarding completed successfully'))
    contextResource.reload()
    router.push({ name: 'Home' })
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    completeLoading.value = false
  }
}

function billingTheme(status) {
  return {
    Active: 'green',
    'Past Due': 'red',
    Suspended: 'orange',
    'Not Configured': 'gray',
  }[status || 'Not Configured']
}
</script>
