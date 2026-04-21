<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __('Billing Addons') }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Configure extra billable services that can be attached to agencies.') }}
        </p>
      </div>
      <Button variant="solid" :label="__('Add Addon')" @click="openCreateDialog" />
    </div>

    <div v-if="addons.loading" class="flex flex-1 items-center justify-center">
      <LoadingIndicator class="size-6" />
    </div>

    <div v-else-if="addons.data?.length" class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div
        v-for="addon in addons.data"
        :key="addon.name"
        class="rounded-lg border border-outline-gray-2 bg-surface-white p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <p class="text-p-base font-semibold text-ink-gray-8">{{ addon.addon_name }}</p>
              <Badge
                :label="addon.active ? __('Active') : __('Inactive')"
                variant="subtle"
                :theme="addon.active ? 'green' : 'gray'"
              />
              <Badge
                v-if="addon.requires_upfront_payment"
                :label="__('Upfront Payment')"
                variant="subtle"
                theme="orange"
              />
            </div>
            <p class="mt-2 text-p-sm text-ink-gray-5">
              {{ addon.pricing_model }} · {{ addon.rate }} {{ addon.currency }}
            </p>
            <p v-if="addon.unit_label" class="mt-1 text-p-xs text-ink-gray-4">
              {{ __('Unit: {0}', [addon.unit_label]) }}
            </p>
            <p v-if="addon.description" class="mt-2 text-p-sm text-ink-gray-5">
              {{ addon.description }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="subtle" :label="__('Edit')" @click="openEditDialog(addon)" />
            <Button variant="subtle" theme="red" :label="__('Delete')" @click="removeAddon(addon)" />
          </div>
        </div>
      </div>
    </div>

    <div v-else class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5 text-p-sm text-ink-gray-5">
      {{ __('No billing addons have been added yet.') }}
    </div>

    <Dialog
      v-model="showDialog"
      :options="{
        title: dialogTitle,
        size: 'md',
        actions: [
          { label: __('Save'), variant: 'solid', onClick: saveAddon },
          { label: __('Cancel'), variant: 'subtle', onClick: () => (showDialog = false) },
        ],
      }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Addon Name') }}</label>
            <input v-model="form.addon_name" :class="inputClass" />
          </div>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Pricing Model') }}</label>
              <select v-model="form.pricing_model" :class="inputClass">
                <option value="Daily Fixed">{{ __('Daily Fixed') }}</option>
                <option value="Monthly Fixed">{{ __('Monthly Fixed') }}</option>
                <option value="Usage Based">{{ __('Usage Based') }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Currency') }}</label>
              <Link
                class="form-control"
                :value="form.currency"
                doctype="Currency"
                @change="(value) => (form.currency = value)"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Rate') }}</label>
              <input v-model="form.rate" type="number" min="0" step="0.01" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Unit Label') }}</label>
              <input v-model="form.unit_label" :class="inputClass" />
            </div>
          </div>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Sort Order') }}</label>
              <input v-model="form.sort_order" type="number" step="1" :class="inputClass" />
            </div>
            <label class="flex items-center gap-2 rounded border border-outline-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
              <input v-model="form.active" type="checkbox" class="h-4 w-4 rounded accent-blue-600" />
              {{ __('Active') }}
            </label>
          </div>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label class="flex items-center gap-2 rounded border border-outline-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
              <input v-model="form.requires_upfront_payment" type="checkbox" class="h-4 w-4 rounded accent-orange-500" />
              {{ __('Requires Upfront Payment') }}
            </label>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Description') }}</label>
            <textarea v-model="form.description" rows="3" :class="inputClass"></textarea>
          </div>
        </div>
      </template>
    </Dialog>

    <ErrorMessage :message="errorMessage" />
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const inputClass =
  'w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100'

const showDialog = ref(false)
const editingName = ref('')
const errorMessage = ref('')

const form = reactive({
  addon_name: '',
  pricing_model: 'Daily Fixed',
  currency: '',
  rate: '',
  unit_label: '',
  active: true,
  requires_upfront_payment: false,
  sort_order: 0,
  description: '',
})

const dialogTitle = computed(() =>
  editingName.value ? __('Edit Billing Addon') : __('Add Billing Addon'),
)

const addons = createResource({
  url: 'crm.api.redtra.billing.list_billing_addons',
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

function resetForm() {
  Object.assign(form, {
    addon_name: '',
    pricing_model: 'Daily Fixed',
    currency: '',
    rate: '',
    unit_label: '',
    active: true,
    requires_upfront_payment: false,
    sort_order: 0,
    description: '',
  })
}

function openCreateDialog() {
  editingName.value = ''
  resetForm()
  showDialog.value = true
}

function openEditDialog(addon) {
  editingName.value = addon.name
  Object.assign(form, {
    addon_name: addon.addon_name || '',
    pricing_model: addon.pricing_model || 'Daily Fixed',
    currency: addon.currency || '',
    rate: addon.rate ?? '',
    unit_label: addon.unit_label || '',
    active: Boolean(addon.active),
    requires_upfront_payment: Boolean(addon.requires_upfront_payment),
    sort_order: addon.sort_order ?? 0,
    description: addon.description || '',
  })
  showDialog.value = true
}

async function saveAddon() {
  errorMessage.value = ''
  try {
    await call('crm.api.redtra.billing.save_billing_addon', {
      name: editingName.value || null,
      data: JSON.stringify({
        addon_name: form.addon_name,
        pricing_model: form.pricing_model,
        currency: form.currency,
        rate: Number(form.rate || 0),
        unit_label: form.unit_label,
        active: form.active ? 1 : 0,
        requires_upfront_payment: form.requires_upfront_payment ? 1 : 0,
        sort_order: Number(form.sort_order || 0),
        description: form.description,
      }),
    })
    toast.success(__('Billing addon saved successfully'))
    showDialog.value = false
    await addons.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

async function removeAddon(addon) {
  if (!window.confirm(__('Delete billing addon {0}?', [addon.addon_name]))) return

  try {
    await call('crm.api.redtra.billing.delete_billing_addon', {
      name: addon.name,
    })
    toast.success(__('Billing addon deleted'))
    await addons.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}
</script>
