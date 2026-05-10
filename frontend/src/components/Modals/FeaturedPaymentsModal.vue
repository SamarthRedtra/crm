<template>
  <Dialog v-model="show" :options="{ size: 'xl' }">
    <template #body>
      <div class="bg-surface-modal rounded-xl border border-outline-gray-2">
        <div class="flex items-start justify-between border-b border-outline-gray-2 px-5 py-4">
          <div>
            <div class="text-xl font-semibold text-ink-gray-9">{{ __('Featured listing payments') }}</div>
            <div class="mt-1 text-sm text-ink-gray-6">
              {{ __('Settle overdue featured listing invoices.') }}
            </div>
          </div>
        </div>

        <div class="space-y-3 px-5 py-4">
          <div
            v-for="item in items"
            :key="item.invoice"
            class="rounded-lg border border-outline-gray-2 px-4 py-3"
          >
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0">
                <div class="truncate font-medium text-ink-gray-8">{{ item.description || item.invoice }}</div>
                <div class="text-sm text-ink-gray-6">
                  {{ __('Due: {0}', [item.due_date || __('N/A')]) }}
                </div>
              </div>
              <div class="text-right">
                <div class="font-semibold text-ink-gray-9">
                  {{ item.currency || currency }} {{ formatMoney(item.amount) }}
                </div>
                <Button size="sm" variant="subtle" @click="paySingle(item)">
                  {{ __('Pay') }}
                </Button>
              </div>
            </div>
          </div>

          <div v-if="!items.length" class="rounded-lg border border-outline-gray-2 px-4 py-6 text-center text-sm text-ink-gray-6">
            {{ __('No overdue featured payments.') }}
          </div>

          <div class="mt-2 rounded-lg border border-outline-gray-2 bg-surface-gray-2 px-4 py-3">
            <div class="flex items-center justify-between text-lg font-semibold">
              <span>{{ __('Total due') }}</span>
              <span>{{ currency }} {{ formatMoney(totalOverdue) }}</span>
            </div>
          </div>
          <ErrorMessage v-if="errorMessage" :message="errorMessage" />
        </div>

        <div class="flex items-center justify-between border-t border-outline-gray-2 px-5 py-4">
          <Button variant="subtle" @click="show = false">{{ __('Close') }}</Button>
          <Button variant="solid" :loading="payingAll" :disabled="!items.length" @click="payAll">
            {{ __('Pay all') }}
          </Button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog, ErrorMessage, call } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  overdues: {
    type: Object,
    default: () => ({}),
  },
})

const show = defineModel()
const errorMessage = ref('')
const payingAll = ref(false)

const items = computed(() => props.overdues?.items || [])
const totalOverdue = computed(() => Number(props.overdues?.total_overdue || 0))
const currency = computed(() => props.overdues?.currency || 'AED')

async function paySingle(item) {
  errorMessage.value = ''
  try {
    const response = await call('crm.api.redtra.billing.pay_agency_invoice', {
      invoice_name: item.invoice,
    })
    const url = response?.stripe_hosted_invoice_url
    if (url) {
      window.open(url, '_blank', 'noopener')
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

async function payAll() {
  if (!items.value.length) return
  payingAll.value = true
  errorMessage.value = ''
  try {
    const responses = await Promise.all(
      items.value.map((item) =>
        call('crm.api.redtra.billing.pay_agency_invoice', {
          invoice_name: item.invoice,
        }),
      ),
    )
    const urls = responses.map((row) => row?.stripe_hosted_invoice_url).filter(Boolean)
    if (urls.length) {
      window.location.href = urls[0]
      urls.slice(1).forEach((url) => window.open(url, '_blank', 'noopener'))
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    payingAll.value = false
  }
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>
