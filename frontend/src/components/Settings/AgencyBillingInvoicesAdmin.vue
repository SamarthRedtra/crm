<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">{{ __('Billing invoices') }}</h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Cross-agency invoice list for CRM managers. Use Agency Billing to pay from an agency context.') }}
        </p>
      </div>
      <Button variant="subtle" :label="__('Refresh')" @click="invoices.reload()" />
    </div>

    <div class="flex flex-wrap gap-3">
      <div class="flex flex-col gap-1">
        <label class="text-p-xs font-medium text-ink-gray-6">{{ __('Status') }}</label>
        <select
          v-model="statusFilter"
          class="rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8"
          @change="onStatusChange"
        >
          <option value="">{{ __('All') }}</option>
          <option value="Draft">{{ __('Draft') }}</option>
          <option value="Open">{{ __('Open') }}</option>
          <option value="Paid">{{ __('Paid') }}</option>
          <option value="Failed">{{ __('Failed') }}</option>
          <option value="Cancelled">{{ __('Cancelled') }}</option>
        </select>
      </div>
    </div>

    <div v-if="invoices.loading" class="flex flex-1 items-center justify-center py-16">
      <LoadingIndicator class="size-8" />
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-outline-gray-2">
      <table class="min-w-full text-left text-p-sm">
        <thead class="border-b border-outline-gray-2 bg-surface-gray-1 text-ink-gray-6">
          <tr>
            <th class="px-4 py-3 font-medium">{{ __('Agency') }}</th>
            <th class="px-4 py-3 font-medium">{{ __('Invoice') }}</th>
            <th class="px-4 py-3 font-medium">{{ __('Status') }}</th>
            <th class="px-4 py-3 font-medium">{{ __('Period') }}</th>
            <th class="px-4 py-3 text-right font-medium">{{ __('Total') }}</th>
            <th class="px-4 py-3 text-right font-medium">{{ __('Paid') }}</th>
            <th class="px-4 py-3 text-right font-medium">{{ __('Due') }}</th>
            <th class="px-4 py-3 font-medium">{{ __('Actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="inv in invoices.data || []"
            :key="inv.name"
            class="border-b border-outline-gray-2 last:border-0"
          >
            <td class="px-4 py-3 text-ink-gray-8">{{ inv.agency_display_name || inv.agency }}</td>
            <td class="px-4 py-3 font-medium text-ink-gray-9">{{ inv.name }}</td>
            <td class="px-4 py-3">
              <Badge :label="inv.status" variant="subtle" :theme="invoiceTheme(inv.status)" />
            </td>
            <td class="px-4 py-3 text-ink-gray-6">
              {{ inv.billing_period_start }} – {{ inv.billing_period_end }}
            </td>
            <td class="px-4 py-3 text-right font-medium text-ink-gray-9">
              {{ formatMoney(inv.total, inv.currency) }}
            </td>
            <td class="px-4 py-3 text-right text-ink-gray-7">
              {{ amountPaid(inv) }}
            </td>
            <td class="px-4 py-3 text-right text-ink-gray-7">
              {{ amountDue(inv) }}
            </td>
            <td class="px-4 py-3">
              <Button
                v-if="inv.stripe_hosted_invoice_url"
                variant="subtle"
                :label="__('Open')"
                @click="openHosted(inv.stripe_hosted_invoice_url)"
              />
              <span v-else class="text-p-sm text-ink-gray-5">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="!invoices.loading && !(invoices.data || []).length" class="text-p-sm text-ink-gray-5">
      {{ __('No invoices yet.') }}
    </p>

    <ErrorMessage :message="errorMessage" />
  </div>
</template>

<script setup>
import {
  Badge,
  Button,
  ErrorMessage,
  LoadingIndicator,
  createResource,
} from 'frappe-ui'
import { ref } from 'vue'

const errorMessage = ref('')
const statusFilter = ref('')

const invoices = createResource({
  url: 'crm.api.redtra.billing.list_all_agency_billing_invoices',
  params: { limit: 80 },
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

function formatMoney(amount, currency) {
  const n = Number(amount || 0)
  return `${n.toFixed(2)} ${currency || ''}`.trim()
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

function amountPaid(inv) {
  if (inv.status === 'Paid') {
    return formatMoney(inv.total, inv.currency)
  }
  return formatMoney(0, inv.currency)
}

function amountDue(inv) {
  if (inv.status === 'Paid') {
    return formatMoney(0, inv.currency)
  }
  return formatMoney(inv.total, inv.currency)
}

function openHosted(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function onStatusChange() {
  invoices.params = {
    limit: 80,
    ...(statusFilter.value ? { status: statusFilter.value } : {}),
  }
  invoices.reload()
}
</script>
