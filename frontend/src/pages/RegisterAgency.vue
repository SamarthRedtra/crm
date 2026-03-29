<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-3xl rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <div class="mb-6">
        <p class="text-xs font-semibold uppercase tracking-wider text-blue-600">{{ __('Redtra CRM') }}</p>
        <h1 class="mt-2 text-2xl font-semibold text-ink-gray-9">{{ __('Register Agency') }}</h1>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Create your agency admin account to start verification, onboarding, and billing setup.') }}
        </p>
      </div>

      <form class="grid grid-cols-1 gap-4 md:grid-cols-2" @submit.prevent="submitRegistration">
        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Admin Full Name') }}</label>
          <input v-model.trim="form.full_name" required :class="inputClass" placeholder="Jane Doe" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Admin Email') }}</label>
          <input v-model.trim="form.email" type="email" required :class="inputClass" placeholder="admin@agency.com" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Password') }}</label>
          <input v-model="form.password" type="password" required minlength="8" :class="inputClass" placeholder="Minimum 8 characters" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Phone') }}</label>
          <PhoneInput v-model="form.phone" :national-placeholder="__('50 000 0000')" />
        </div>

        <div class="flex flex-col gap-1.5 md:col-span-2">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Agency Name') }}</label>
          <input v-model.trim="form.agency_name" required :class="inputClass" placeholder="Acme Properties" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Agency Email') }}</label>
          <input v-model.trim="form.agency_email" type="email" :class="inputClass" placeholder="hello@agency.com" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Agency Phone') }}</label>
          <PhoneInput v-model="form.agency_phone" :national-placeholder="__('4 000 0000')" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Website') }}</label>
          <input v-model.trim="form.website" :class="inputClass" placeholder="https://agency.ae" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('BRN ID') }}</label>
          <input v-model.trim="form.brn_id" :class="inputClass" placeholder="BRN-12345" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Contact Name') }}</label>
          <input v-model.trim="form.billing_contact_name" :class="inputClass" placeholder="Finance Manager" />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Email') }}</label>
          <input v-model.trim="form.billing_email" type="email" :class="inputClass" placeholder="billing@agency.com" />
        </div>

        <div class="md:col-span-2 flex items-start gap-2 rounded border border-outline-gray-2 bg-surface-gray-1 p-3">
          <input id="accept-terms" v-model="form.accept_terms" type="checkbox" class="mt-1" />
          <label for="accept-terms" class="text-p-sm text-ink-gray-6">
            {{ __('I confirm that this information is accurate and agree to verification and billing policy checks.') }}
          </label>
        </div>

        <div class="md:col-span-2 rounded border border-outline-gray-2 bg-surface-gray-1 p-3">
          <p class="text-p-sm font-medium text-ink-gray-7">{{ challengePrompt || __('Security challenge loading...') }}</p>
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
import { Button, ErrorMessage, call } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

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
