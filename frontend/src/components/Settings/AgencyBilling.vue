<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __('Agency Billing') }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Daily charges accrue automatically and invoices are raised monthly for your agency.') }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          v-if="data?.context?.can_manage_billing"
          variant="subtle"
          :label="__('Set Up Billing Method')"
          @click="startSetup"
        />
        <Button
          v-if="data?.context?.is_internal_manager"
          variant="solid"
          :label="__('Close Previous Month')"
          :loading="closeMonthLoading"
          @click="closePreviousMonth"
        />
      </div>
    </div>

    <div v-if="management.loading" class="flex flex-1 items-center justify-center">
      <LoadingIndicator class="size-6" />
    </div>

    <template v-else-if="data?.agency">
      <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
          <p class="text-p-sm text-ink-gray-5">{{ __('Current Period') }}</p>
          <p class="mt-2 text-2xl font-semibold text-ink-gray-9">
            {{ formatMoney(data.current_period?.total_amount, data.current_period?.currency) }}
          </p>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{ data.current_period?.period_start }} - {{ data.current_period?.period_end }}
          </p>
        </div>

        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
          <p class="text-p-sm text-ink-gray-5">{{ __('Open Entries') }}</p>
          <p class="mt-2 text-2xl font-semibold text-ink-gray-9">
            {{ data.current_period?.entry_count || 0 }}
          </p>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{ __('Agent level and addon charges waiting to be invoiced.') }}
          </p>
        </div>

        <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
          <p class="text-p-sm text-ink-gray-5">{{ __('Billing Status') }}</p>
          <div class="mt-2 flex items-center gap-2">
            <Badge
              :label="data.agency.billing_status || __('Not Configured')"
              variant="subtle"
              :theme="billingTheme(data.agency.billing_status)"
            />
            <Badge
              :label="data.agency.onboarding_status || __('Not Started')"
              variant="subtle"
              theme="blue"
            />
          </div>
          <p class="mt-2 text-p-sm text-ink-gray-5">
            {{
              !data.billing_enabled
                ? __('Billing is currently disabled by CRM managers.')
                : data.stripe_enabled
                ? __('Stripe is enabled for invoice collection.')
                : __('Stripe keys are not configured yet. You can still accrue charges and invoice later.')
            }}
          </p>
        </div>
      </div>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-p-base font-semibold text-ink-gray-8">
              {{ __('Saved Cards') }}
            </h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('Save multiple cards securely with Stripe and choose the default card for automatic charges.') }}
            </p>
          </div>
          <Button
            v-if="data?.context?.can_manage_billing"
            variant="subtle"
            :label="__('Add Card')"
            @click="addCard"
          />
        </div>

        <div v-if="savedCards.length" class="overflow-x-auto rounded-lg border border-outline-gray-2">
          <table class="min-w-full text-left text-p-sm">
            <thead class="border-b border-outline-gray-2 bg-surface-gray-1 text-ink-gray-6">
              <tr>
                <th class="px-4 py-3 font-medium">{{ __('Card') }}</th>
                <th class="px-4 py-3 font-medium">{{ __('Expiry') }}</th>
                <th class="px-4 py-3 font-medium">{{ __('Added') }}</th>
                <th class="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="card in savedCards"
                :key="card.stripe_payment_method_id"
                class="border-b border-outline-gray-2 last:border-0"
              >
                <td class="px-4 py-3">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="font-medium text-ink-gray-8">{{ formatCardLabel(card) }}</span>
                    <Badge
                      v-if="card.is_default"
                      :label="__('Default')"
                      variant="subtle"
                      theme="green"
                    />
                    <Badge
                      :label="card.status || __('Active')"
                      variant="subtle"
                      :theme="card.status === 'Detached' ? 'gray' : 'blue'"
                    />
                  </div>
                </td>
                <td class="px-4 py-3 text-ink-gray-7">{{ formatCardExpiry(card) }}</td>
                <td class="px-4 py-3 text-ink-gray-6">{{ formatCardAdded(card) }}</td>
                <td class="px-4 py-3 text-right">
                  <div
                    v-if="data?.context?.can_manage_billing && card.status !== 'Detached'"
                    class="flex flex-wrap justify-end gap-2"
                  >
                    <Button
                      v-if="!card.is_default"
                      variant="subtle"
                      :label="__('Set Default')"
                      :loading="settingDefaultId === card.stripe_payment_method_id"
                      @click="setDefault(card)"
                    />
                    <Button
                      variant="subtle"
                      theme="red"
                      :label="__('Remove')"
                      :loading="detachingId === card.stripe_payment_method_id"
                      @click="detachCard(card)"
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-5">
          {{ __('No cards saved yet. Add a card to enable easy default-card switching and future billing.') }}
        </div>
      </section>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <div class="mb-4">
          <h3 class="text-p-base font-semibold text-ink-gray-8">
            {{ __('Current Period Breakdown') }}
          </h3>
        </div>

        <div v-if="data.current_period?.items?.length" class="overflow-x-auto">
          <table class="min-w-full text-left text-p-sm">
            <thead class="text-ink-gray-5">
              <tr>
                <th class="pb-3 font-medium">{{ __('Description') }}</th>
                <th class="pb-3 font-medium">{{ __('Quantity') }}</th>
                <th class="pb-3 font-medium">{{ __('Rate') }}</th>
                <th class="pb-3 text-right font-medium">{{ __('Amount') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in data.current_period.items"
                :key="`${item.description}-${item.agent || item.addon || ''}`"
                class="border-t border-outline-gray-2"
              >
                <td class="py-3 text-ink-gray-7">{{ item.description }}</td>
                <td class="py-3 text-ink-gray-6">{{ item.quantity }}</td>
                <td class="py-3 text-ink-gray-6">
                  {{ formatMoney(item.rate, data.current_period.currency) }}
                </td>
                <td class="py-3 text-right font-medium text-ink-gray-8">
                  {{ formatMoney(item.amount, data.current_period.currency) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-5">
          {{ __('No accruals have been generated for the current period yet.') }}
        </div>
      </section>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-p-base font-semibold text-ink-gray-8">
              {{ __('Invoices') }}
            </h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('Monthly invoices for this agency. Agency admins can open and pay unpaid invoices.') }}
            </p>
          </div>
          <Button variant="subtle" :label="__('Refresh')" @click="management.reload()" />
        </div>

        <div v-if="data.invoices?.length" class="flex flex-col gap-3">
          <div
            v-for="invoice in data.invoices"
            :key="invoice.name"
            class="rounded-lg border border-outline-gray-2 px-4 py-4"
          >
            <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <p class="text-p-base font-medium text-ink-gray-8">{{ invoice.name }}</p>
                  <Badge :label="invoice.status" variant="subtle" :theme="invoiceTheme(invoice.status)" />
                </div>
                <p class="mt-1 text-p-sm text-ink-gray-5">
                  {{ invoice.billing_period_start }} - {{ invoice.billing_period_end }}
                </p>
              </div>

              <div class="flex flex-wrap items-center gap-3">
                <p class="text-p-base font-semibold text-ink-gray-9">
                  {{ formatMoney(invoice.total, invoice.currency) }}
                </p>
                <Button
                  v-if="canOpenInvoice(invoice)"
                  variant="solid"
                  :label="__('Open Invoice')"
                  :loading="openingInvoice === invoice.name"
                  @click="openInvoice(invoice)"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-else class="rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-5">
          {{ __('No invoices have been generated yet.') }}
        </div>
      </section>
    </template>

    <StripeSetupPaymentModal
      v-model="showStripeModal"
      :agency-id="data?.agency?.name"
      :intent="stripeModalIntent"
      return-path="/crm/settings?section=billing"
      @success="onStripeCardSaved"
    />

    <ErrorMessage :message="errorMessage" />
  </div>
</template>

<script setup>
import StripeSetupPaymentModal from '@/components/Billing/StripeSetupPaymentModal.vue'
import { finalizeStripeSetupReturn } from '@/composables/stripeSetupReturn'
import { agencyStore } from '@/stores/agency'
import {
  Badge,
  Button,
  ErrorMessage,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const { contextResource } = agencyStore()

const errorMessage = ref('')
const showStripeModal = ref(false)
const stripeModalIntent = ref('billing_setup')
const closeMonthLoading = ref(false)
const openingInvoice = ref('')
const settingDefaultId = ref('')
const detachingId = ref('')

const management = createResource({
  url: 'crm.api.redtra.billing.get_agency_management_data',
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

const data = computed(() => management.data || {})
const savedCards = computed(() => data.value.saved_payment_methods || [])

function formatMoney(amount, currency) {
  const numeric = Number(amount || 0)
  return `${numeric.toFixed(2)} ${currency || ''}`.trim()
}

function billingTheme(status) {
  return {
    Active: 'green',
    'Past Due': 'red',
    Suspended: 'orange',
    'Not Configured': 'gray',
  }[status || 'Not Configured']
}

function invoiceTheme(status) {
  return {
    Paid: 'green',
    Open: 'blue',
    Failed: 'red',
    Draft: 'orange',
    Cancelled: 'gray',
  }[status || 'Draft']
}

function canOpenInvoice(invoice) {
  return (
    data.value.context?.can_manage_billing &&
    ['Draft', 'Open', 'Failed'].includes(invoice.status)
  )
}

function formatCardLabel(card) {
  const brand = (card.brand || __('Card')).toUpperCase()
  const last4 = card.last4 || '----'
  return `${brand} **** ${last4}`
}

function formatCardExpiry(card) {
  const month = Number(card.exp_month || 0)
  const year = Number(card.exp_year || 0)
  if (!month || !year) return '--/--'
  return `${String(month).padStart(2, '0')}/${year}`
}

function formatCardAdded(card) {
  if (!card.added_on) return '—'
  try {
    return new Date(card.added_on).toLocaleString()
  } catch {
    return card.added_on
  }
}

async function onStripeCardSaved() {
  toast.success(__('Card saved successfully'))
  await management.reload()
  contextResource.reload()
}

async function startSetup() {
  if (!data.value.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  if (!data.value.stripe_enabled) {
    errorMessage.value = __('Stripe is not configured for billing.')
    return
  }
  errorMessage.value = ''
  stripeModalIntent.value = 'billing_setup'
  showStripeModal.value = true
}

async function addCard() {
  if (!data.value.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  if (!data.value.stripe_enabled) {
    errorMessage.value = __('Stripe is not configured for billing.')
    return
  }
  errorMessage.value = ''
  stripeModalIntent.value = 'add_card'
  showStripeModal.value = true
}

watch(
  () => [route.fullPath, management.data?.agency?.name],
  async () => {
    if (!management.data?.agency?.name) return
    await finalizeStripeSetupReturn({
      route,
      router,
      agencyId: management.data.agency.name,
      onSuccess: onStripeCardSaved,
    })
  },
  { immediate: true },
)

async function setDefault(card) {
  settingDefaultId.value = card.stripe_payment_method_id
  errorMessage.value = ''
  try {
    await call('crm.api.redtra.billing.set_default_payment_method', {
      agency_id: data.value.agency.name,
      stripe_payment_method_id: card.stripe_payment_method_id,
    })
    toast.success(__('Default card updated'))
    await management.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    settingDefaultId.value = ''
  }
}

async function detachCard(card) {
  detachingId.value = card.stripe_payment_method_id
  errorMessage.value = ''
  try {
    await call('crm.api.redtra.billing.detach_payment_method', {
      agency_id: data.value.agency.name,
      stripe_payment_method_id: card.stripe_payment_method_id,
    })
    toast.success(__('Card removed'))
    await management.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    detachingId.value = ''
  }
}

async function closePreviousMonth() {
  if (!data.value.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  closeMonthLoading.value = true
  errorMessage.value = ''
  try {
    await call('crm.api.redtra.billing.close_agency_billing_period', {
      agency_id: data.value.agency.name,
    })
    toast.success(__('Previous month billing has been closed'))
    await management.reload()
    contextResource.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    closeMonthLoading.value = false
  }
}

async function openInvoice(invoice) {
  if (!data.value.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  openingInvoice.value = invoice.name
  errorMessage.value = ''
  try {
    const response = await call('crm.api.redtra.billing.pay_agency_invoice', {
      invoice_name: invoice.name,
    })
    if (response?.stripe_hosted_invoice_url) {
      window.location.href = response.stripe_hosted_invoice_url
      return
    }
    toast.success(__('Invoice refreshed successfully'))
    await management.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    openingInvoice.value = ''
  }
}
</script>
