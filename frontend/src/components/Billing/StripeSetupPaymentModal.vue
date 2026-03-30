<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title: dialogTitle, size: '3xl' }"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <template #body>
      <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-xl font-semibold text-ink-gray-9">{{ dialogTitle }}</h3>
        </div>
        <div v-if="loading" class="flex min-h-[220px] items-center justify-center">
          <LoadingIndicator class="size-8" />
        </div>
        <div v-show="!loading" ref="mountEl" class="min-h-[200px]" />
        <p v-if="errorMessage" class="mt-3 text-p-sm text-red-600">{{ errorMessage }}</p>
        <div class="mt-6 flex flex-col gap-3 border-t border-outline-gray-2 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-p-xs text-ink-gray-5">
            {{ __('Payments are processed securely by Stripe.') }}
          </p>
          <Button
            variant="solid"
            :label="__('Verify & Save Card')"
            :loading="submitting"
            :disabled="loading || !ready"
            @click="submit"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { loadStripe } from '@stripe/stripe-js'
import { Button, Dialog, LoadingIndicator, call } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** Agency name (omit for current session agency). */
  agencyId: { type: String, default: '' },
  /** billing_setup | add_card */
  intent: { type: String, default: 'billing_setup' },
  /** Path + query only, e.g. /crm/settings?section=billing */
  returnPath: { type: String, default: '/crm/settings?section=billing' },
})

const emit = defineEmits(['update:modelValue', 'success'])

const mountEl = ref(null)
const loading = ref(false)
const submitting = ref(false)
const ready = ref(false)
const errorMessage = ref('')

let stripeRef = null
let elementsRef = null
let paymentElementRef = null

const dialogTitle = computed(() =>
  props.intent === 'add_card' ? __('Add new card') : __('Set up billing method'),
)

function buildReturnUrl() {
  const path = props.returnPath.startsWith('/') ? props.returnPath : `/${props.returnPath}`
  const sep = path.includes('?') ? '&' : '?'
  return `${window.location.origin}${path}${sep}stripe_setup=1`
}

function teardown() {
  try {
    paymentElementRef?.unmount?.()
  } catch {
    // ignore
  }
  paymentElementRef = null
  elementsRef = null
  stripeRef = null
  ready.value = false
  if (mountEl.value) {
    mountEl.value.innerHTML = ''
  }
}

async function initStripe() {
  errorMessage.value = ''
  loading.value = true
  ready.value = false
  teardown()
  try {
    const res = await call('crm.api.redtra.billing.create_stripe_setup_intent', {
      agency_id: props.agencyId || undefined,
      intent: props.intent,
    })
    if (!res?.client_secret || !res?.publishable_key) {
      errorMessage.value = __('Could not start card setup. Check Stripe keys in Agency Billing Settings.')
      return
    }
    await nextTick()
    const stripe = await loadStripe(res.publishable_key)
    if (!stripe) {
      errorMessage.value = __('Failed to load Stripe.')
      return
    }
    stripeRef = stripe
    const elements = stripe.elements({
      clientSecret: res.client_secret,
      appearance: { theme: 'stripe' },
    })
    elementsRef = elements
    const paymentElement = elements.create('payment', { layout: 'tabs' })
    paymentElement.mount(mountEl.value)
    paymentElementRef = paymentElement
    ready.value = true
  } catch (e) {
    errorMessage.value = e?.messages?.[0] || e?.message || __('Setup failed.')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!stripeRef || !elementsRef) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const returnUrl = buildReturnUrl()
    const { error, setupIntent } = await stripeRef.confirmSetup({
      elements: elementsRef,
      confirmParams: {
        return_url: returnUrl,
      },
      redirect: 'if_required',
    })
    if (error) {
      errorMessage.value = error.message || __('Verification failed.')
      return
    }
    if (setupIntent?.status === 'succeeded' && setupIntent.id) {
      await call('crm.api.redtra.billing.complete_stripe_setup_intent', {
        setup_intent_id: setupIntent.id,
        agency_id: props.agencyId || undefined,
      })
      emit('success')
      emit('update:modelValue', false)
      teardown()
    }
  } catch (e) {
    errorMessage.value = e?.messages?.[0] || e?.message || __('Verification failed.')
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      await nextTick()
      await initStripe()
    } else {
      teardown()
    }
  },
)
</script>
