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
          :loading="setupLoading"
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

    <ErrorMessage :message="errorMessage" />
  </div>
</template>

<script setup>
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
import { computed, ref } from 'vue'

const { contextResource } = agencyStore()

const errorMessage = ref('')
const setupLoading = ref(false)
const closeMonthLoading = ref(false)
const openingInvoice = ref('')

const management = createResource({
  url: 'crm.api.redtra.billing.get_agency_management_data',
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

const data = computed(() => management.data || {})

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

async function startSetup() {
  if (!data.value.billing_enabled) {
    errorMessage.value = __('Billing is disabled in Agency Billing Settings')
    return
  }
  setupLoading.value = true
  errorMessage.value = ''
  try {
    const successUrl = `${window.location.origin}/crm/agency-onboarding?billing=success`
    const cancelUrl = `${window.location.origin}/crm/agency-onboarding?billing=cancel`
    const response = await call('crm.api.redtra.billing.create_billing_setup_session', {
      agency_id: data.value.agency.name,
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
