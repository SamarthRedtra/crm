<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-3xl rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <div class="mb-6">
        <div v-if="brandResource.data?.brand_logo" class="mb-3">
          <img
            :src="brandResource.data.brand_logo"
            :alt="displayBrandName"
            class="h-12 w-auto max-w-[220px] object-contain object-left"
          />
        </div>
        <p v-else class="text-xs font-semibold uppercase tracking-wider text-blue-600">{{ displayBrandName }}</p>
        <h1 class="mt-2 text-2xl font-semibold text-ink-gray-9">{{ __('Register Agency') }}</h1>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Create your agency admin account to start verification, onboarding, and billing setup.') }}
        </p>
      </div>

      <div
        v-if="billingPreview.data"
        class="mb-6 rounded-lg border border-outline-blue-1 bg-surface-blue-1 p-4 text-p-sm text-ink-gray-7"
      >
        <p class="font-medium text-ink-gray-8">{{ __('Billing & subscription (how it works)') }}</p>
        <ul class="mt-2 list-inside list-disc space-y-1">
          <li>
            {{
              __(
                'After signup: agency verification, then Agency Onboarding where you add billing details and payment method when required.',
              )
            }}
          </li>
          <li v-if="billingPreview.data.billing_enabled">
            {{
              __('Payment timing: {0}', [
                paymentModeLabel(billingPreview.data.payment_mode),
              ])
            }}
          </li>
          <li v-else>{{ __('Subscription billing may be enabled by your CRM administrator after onboarding.') }}</li>
          <li v-if="billingPreview.data.trial_enabled">
            {{
              __('Trial: up to {0} days (plus {1} grace days if configured).', [
                billingPreview.data.trial_days,
                billingPreview.data.trial_grace_days,
              ])
            }}
            <span v-if="billingPreview.data.trial_requires_payment_method">
              {{ __(' A card on file may be required to start the trial.') }}
            </span>
          </li>
          <li>
            {{
              __(
                'One base per-agent daily rate applies to billable team members; optional add-ons are configured in Settings → Agency Profile after signup.',
              )
            }}
          </li>
        </ul>

        <div
          v-if="baseAgentLevel"
          class="mt-3 rounded border border-outline-blue-1 bg-surface-white px-3 py-2"
        >
          <p class="text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Base agent rate (per day)') }}</p>
          <div class="mt-1 flex justify-between gap-2 text-p-sm text-ink-gray-8">
            <span>{{ baseAgentLevel.level_name }}</span>
            <span class="shrink-0 font-medium tabular-nums">
              {{ formatCatalogMoney(baseAgentLevel.daily_rate, baseAgentLevel.currency || billingPreview.data.default_currency) }}
            </span>
          </div>
        </div>

        <div
          v-if="(billingPreview.data.billing_addons || []).length"
          class="mt-2 rounded border border-outline-blue-1 bg-surface-white px-3 py-2"
        >
          <p class="text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Optional add-ons (catalog)') }}</p>
          <ul class="mt-1 space-y-1 text-p-sm text-ink-gray-8">
            <li v-for="ad in billingPreview.data.billing_addons" :key="ad.name" class="flex justify-between gap-2">
              <span class="min-w-0 flex-1">
                {{ ad.addon_name }}
                <span v-if="ad.unit_label" class="text-p-xs text-ink-gray-5">({{ ad.unit_label }})</span>
              </span>
              <span class="shrink-0 font-medium tabular-nums">
                {{ formatCatalogMoney(ad.rate, ad.currency || billingPreview.data.default_currency) }}
                <span v-if="ad.pricing_model" class="text-p-xs font-normal text-ink-gray-5"> · {{ ad.pricing_model }}</span>
              </span>
            </li>
          </ul>
        </div>

        <p v-if="!hasCatalogRows" class="mt-2 text-p-xs text-ink-gray-5">
          {{
            __(
              'List prices appear here once your administrator configures the base Agent Level and Billing Addons in Desk.',
            )
          }}
        </p>

        <p class="mt-2 text-p-xs text-ink-gray-5">
          {{ __('Default billing currency: {0}', [billingPreview.data.default_currency]) }}
        </p>
      </div>

      <form class="grid grid-cols-1 gap-4 md:grid-cols-2" @submit.prevent="submitRegistration">
        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Admin Full Name') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.full_name" required :class="inputClass" placeholder="Jane Doe" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Admin Email') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.email" type="email" required :class="inputClass" placeholder="admin@agency.com" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Password') }} <span class="text-red-600">*</span>
          </label>
          <div class="relative w-full">
            <input v-model="form.password" :type="showPassword ? 'text' : 'password'" required minlength="8" :class="[inputClass, 'pr-10']" placeholder="Minimum 8 characters" />
            <button
              type="button"
              class="absolute inset-y-0 right-0 flex items-center pr-3 text-ink-gray-5 hover:text-ink-gray-7 focus:outline-none"
              @click="showPassword = !showPassword"
              tabindex="-1"
            >
              <FeatherIcon :name="showPassword ? 'eye-off' : 'eye'" class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Phone') }} <span class="text-red-600">*</span>
          </label>
          <PhoneInput v-model="form.phone" required :national-placeholder="__('50 000 0000')" />
        </div>

        <div class="flex flex-col gap-1.5 md:col-span-2">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Agency Name') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.agency_name" required :class="inputClass" placeholder="Acme Properties" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Agency Email') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.agency_email" type="email" required :class="inputClass" placeholder="hello@agency.com" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Agency Phone') }} <span class="text-red-600">*</span>
          </label>
          <PhoneInput v-model="form.agency_phone" required :national-placeholder="__('4 000 0000')" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Website') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.website" type="url" required :class="inputClass" placeholder="https://agency.ae" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('BRN ID') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.brn_id" required :class="inputClass" placeholder="BRN-12345" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Billing Contact Name') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.billing_contact_name" required :class="inputClass" placeholder="Finance Manager" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">
            {{ __('Billing Email') }} <span class="text-red-600">*</span>
          </label>
          <input v-model.trim="form.billing_email" type="email" required :class="inputClass" placeholder="billing@agency.com" />
        </div>

        <div class="md:col-span-2 flex items-start gap-2 rounded border border-outline-gray-2 bg-surface-gray-1 p-3">
          <input id="accept-terms" v-model="form.accept_terms" type="checkbox" required class="mt-1" />
          <label for="accept-terms" class="text-p-sm text-ink-gray-6">
            <span class="text-red-600">*</span>
            {{ __('I confirm that this information is accurate and agree to verification and billing policy checks.') }}
          </label>
        </div>

        <div class="md:col-span-2 rounded border border-outline-gray-2 bg-surface-gray-1 p-3">
          <p class="text-p-sm font-medium text-ink-gray-7">
            {{ challengePrompt || __('Security challenge loading...') }} <span class="text-red-600">*</span>
          </p>
          <div class="mt-2 flex gap-2">
            <input
              v-model.trim="form.challenge_answer"
              required
              :class="inputClass"
              :placeholder="__('Enter answer')"
            />
            <Button type="button" variant="subtle" :label="__('Refresh')" @click="fetchChallenge" />
          </div>
        </div>

        <div class="md:col-span-2 flex flex-col gap-3">
          <Button
            variant="solid"
            type="submit"
            :loading="isSubmitting"
            :label="isSubmitting ? __('Creating account...') : __('Register Agency')"
            :disabled="!form.accept_terms"
          />
          <Button type="button" variant="ghost" :label="__('Back to Login')" @click="router.push({ name: 'CRM Login' })" />
        </div>
      </form>

      <ErrorMessage class="mt-4" :message="errorMessage" />
      <div
        v-if="successMessage"
        class="mt-4 rounded-lg border border-outline-green-1 bg-surface-green-1 px-4 py-3 text-p-sm text-green-700"
      >
        {{ successMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import PhoneInput from '@/components/PhoneInput.vue'
import { Button, ErrorMessage, call, createResource } from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const billingPreview = createResource({
  url: 'crm.api.redtra.billing.public_billing_preview',
  auto: true,
  onError() {
    // Page works without preview
  },
})

const brandResource = createResource({
  url: 'crm.api.auth.public_brand',
  auto: true,
  onError() {
    // Branding is optional; fall back to default title.
  },
})

const displayBrandName = computed(() => {
  const name = brandResource.data?.brand_name?.trim()
  return name || __('Redtra CRM')
})

function paymentModeLabel(mode) {
  const m = mode || 'two_step'
  if (m === 'two_step') {
    return __('Card setup first; charges after agency verification (default)')
  }
  if (m === 'after_verification') {
    return __('Billing starts after agency verification')
  }
  if (m === 'before_verification') {
    return __('Billing may start before agency verification')
  }
  return m
}

function formatCatalogMoney(amount, currency) {
  const n = Number(amount ?? 0)
  const c = currency || 'USD'
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: c }).format(n)
  } catch {
    return `${n} ${c}`
  }
}

const baseAgentLevel = computed(() => {
  const d = billingPreview.data
  if (!d) return null
  if (d.agent_level) return d.agent_level
  const list = d.agent_levels || []
  return list[0] || null
})

const hasCatalogRows = computed(() => {
  const d = billingPreview.data
  if (!d) return false
  const hasBase = !!(d.agent_level || (d.agent_levels || []).length)
  const addons = d.billing_addons?.length || 0
  return hasBase || addons > 0
})

const inputClass =
  'w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100'

const form = reactive({
  full_name: '',
  email: '',
  password: '',
  phone: '',
  agency_name: '',
  agency_email: '',
  agency_phone: '',
  website: '',
  brn_id: '',
  billing_contact_name: '',
  billing_email: '',
  challenge_answer: '',
  accept_terms: false,
})

const isSubmitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const showPassword = ref(false)
const challengeId = ref('')
const challengePrompt = ref('')
const idempotencyKey = ref(`agency-signup-${Date.now()}-${Math.random().toString(36).slice(2)}`)

async function submitRegistration() {
  errorMessage.value = ''
  successMessage.value = ''
  isSubmitting.value = true
  try {
    const response = await call('crm.api.redtra.onboarding.register_agency_admin', {
      data: JSON.stringify({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        phone: form.phone,
        agency_name: form.agency_name,
        agency_email: form.agency_email,
        agency_phone: form.agency_phone,
        website: form.website,
        brn_id: form.brn_id,
        billing_contact_name: form.billing_contact_name,
        billing_email: form.billing_email,
        challenge_id: challengeId.value,
        challenge_answer: form.challenge_answer,
        idempotency_key: idempotencyKey.value,
      }),
    })

    successMessage.value =
      response?.message || __('Agency registration submitted. Please login to continue onboarding.')
    setTimeout(() => {
      router.push({ name: 'CRM Login' })
    }, 1200)
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
    await fetchChallenge()
  } finally {
    isSubmitting.value = false
  }
}

async function fetchChallenge() {
  try {
    const response = await call('crm.api.redtra.onboarding.get_registration_challenge')
    challengeId.value = response?.challenge_id || ''
    challengePrompt.value = response?.prompt || ''
    form.challenge_answer = ''
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

onMounted(() => {
  fetchChallenge()
})
</script>
