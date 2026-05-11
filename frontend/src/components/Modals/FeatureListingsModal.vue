<template>
  <Dialog v-model="show" :options="{ size: 'xl' }">
    <template #body>
      <div class="bg-surface-modal rounded-xl border border-outline-gray-2">
        <div class="border-b border-outline-gray-2 px-5 py-4">
          <div class="text-xl font-semibold text-ink-gray-9">{{ __('Feature listings') }}</div>
          <div class="mt-1 text-sm text-ink-gray-6">
            {{ __('Pay for featured visibility for selected properties.') }}
          </div>
        </div>

        <div class="space-y-5 px-5 py-4">
          <div>
            <div class="mb-2 text-sm font-medium text-ink-gray-7">{{ __('Duration') }}</div>
            <div class="flex flex-wrap gap-2">
              <Button
                v-for="days in durationOptions"
                :key="days"
                size="sm"
                :variant="selectedDuration === days ? 'solid' : 'subtle'"
                @click="applyDuration(days)"
              >
                {{ __('{0} day(s)', [days]) }}
              </Button>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div>
              <div class="mb-1.5 text-sm text-ink-gray-7">{{ __('Start date') }}</div>
              <DatePicker
                :modelValue="startDate"
                :format="'YYYY-MM-DD'"
                :placeholder="__('Select start date')"
                @update:modelValue="(v) => (startDate = normalizeDateOutputFromPicker(v))"
              />
            </div>
            <div>
              <div class="mb-1.5 text-sm text-ink-gray-7">{{ __('End date') }}</div>
              <DatePicker
                :modelValue="endDate"
                :format="'YYYY-MM-DD'"
                :placeholder="__('Select end date')"
                @update:modelValue="(v) => (endDate = normalizeDateOutputFromPicker(v))"
              />
            </div>
          </div>

          <div class="rounded-lg border border-outline-gray-2 bg-surface-gray-2 p-4">
            <div class="grid grid-cols-2 gap-y-2 text-sm">
              <div class="text-ink-gray-6">{{ __('Properties') }}</div>
              <div class="text-right font-medium text-ink-gray-8">{{ propertyCount }}</div>
              <div class="text-ink-gray-6">{{ __('Duration') }}</div>
              <div class="text-right font-medium text-ink-gray-8">{{ featuredDays }} {{ __('day(s)') }}</div>
              <div class="text-ink-gray-6">{{ __('Rate') }}</div>
              <div class="text-right font-medium text-ink-gray-8">
                {{ currency }} {{ formatMoney(dailyRate) }} / {{ __('day') }}
              </div>
            </div>
            <div class="mt-3 border-t border-outline-gray-2 pt-3 text-lg font-semibold text-ink-amber-3">
              <div class="flex items-center justify-between">
                <span>{{ __('Total') }}</span>
                <span>{{ currency }} {{ formatMoney(totalAmount) }}</span>
              </div>
            </div>
          </div>
          <ErrorMessage v-if="errorMessage" :message="errorMessage" />
        </div>

        <div class="flex items-center justify-between border-t border-outline-gray-2 px-5 py-4">
          <Button variant="subtle" @click="show = false">{{ __('Cancel') }}</Button>
          <Button variant="solid" :loading="submitting" @click="checkoutFeatured">
            {{ __('Confirm & feature') }}
          </Button>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, DatePicker, Dialog, ErrorMessage, call } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { normalizeDateOutputFromPicker } from '@/utils'

const props = defineProps({
  selectedProperties: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['checkoutCreated'])
const show = defineModel()

const durationOptions = [1, 3, 7, 14, 30]
const selectedDuration = ref(14)
const startDate = ref(toDateInput(new Date()))
const endDate = ref(toDateInput(addDays(new Date(), selectedDuration.value - 1)))
const dailyRate = ref(0)
const currency = ref('AED')
const submitting = ref(false)
const errorMessage = ref('')

const propertyCount = computed(() => props.selectedProperties.length)
const featuredDays = computed(() => {
  if (!startDate.value || !endDate.value) return 0
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  const diff = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1
  return diff > 0 ? diff : 0
})
const totalAmount = computed(() => propertyCount.value * featuredDays.value * Number(dailyRate.value || 0))
const propertyIds = computed(() =>
  props.selectedProperties
    .map((row) => row.name || row.property_id || row.id)
    .filter(Boolean),
)

watch(startDate, (value) => {
  if (!value || !selectedDuration.value) return
  endDate.value = toDateInput(addDays(new Date(value), selectedDuration.value - 1))
})

watch([startDate, endDate], () => {
  const days = featuredDays.value
  if (!durationOptions.includes(days)) {
    selectedDuration.value = null
  }
})

function applyDuration(days) {
  selectedDuration.value = days
  if (!startDate.value) {
    startDate.value = toDateInput(new Date())
  }
  endDate.value = toDateInput(addDays(new Date(startDate.value), days - 1))
}

async function loadFeaturedRate() {
  try {
    const addons = await call('crm.api.redtra.billing.list_billing_addons', { active_only: 1 })
    const featuredAddon = (addons || []).find((row) => row.addon_name === 'Featured Listings')
      || (addons || []).find((row) => (row.addon_name || '').toLowerCase().includes('featured'))
    if (featuredAddon) {
      dailyRate.value = Number(featuredAddon.rate || 0)
      currency.value = featuredAddon.currency || 'AED'
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

async function checkoutFeatured() {
  if (!propertyIds.value.length) {
    errorMessage.value = __('Please select at least one property.')
    return
  }
  if (!startDate.value || !endDate.value || featuredDays.value <= 0) {
    errorMessage.value = __('Please choose a valid featured date range.')
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    const response = await call('crm.api.redtra.billing.create_featured_checkout_session', {
      property_ids: propertyIds.value,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    emit('checkoutCreated', response)
    if (response?.url) {
      window.location.href = response.url
      return
    }
    errorMessage.value = __('Failed to initialize checkout session.')
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    submitting.value = false
  }
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function addDays(date, days) {
  const cloned = new Date(date)
  cloned.setDate(cloned.getDate() + days)
  return cloned
}

function toDateInput(value) {
  const d = new Date(value)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

onMounted(loadFeaturedRate)
</script>
