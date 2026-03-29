<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __('Agent Level Pricing') }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Define the daily subscription value for each agent level.') }}
        </p>
      </div>
      <Button variant="solid" :label="__('Add Level')" @click="openCreateDialog" />
    </div>

    <div v-if="levels.loading" class="flex flex-1 items-center justify-center">
      <LoadingIndicator class="size-6" />
    </div>

    <div v-else-if="levels.data?.length" class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <div
        v-for="level in levels.data"
        :key="level.name"
        class="rounded-lg border border-outline-gray-2 bg-surface-white p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2">
              <p class="text-p-base font-semibold text-ink-gray-8">{{ level.level_name }}</p>
              <Badge
                :label="level.active ? __('Active') : __('Inactive')"
                variant="subtle"
                :theme="level.active ? 'green' : 'gray'"
              />
            </div>
            <p class="mt-2 text-p-lg font-semibold text-ink-gray-9">
              {{ level.daily_rate }} {{ level.currency }}
            </p>
            <p v-if="level.description" class="mt-1 text-p-sm text-ink-gray-5">
              {{ level.description }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="subtle" :label="__('Edit')" @click="openEditDialog(level)" />
            <Button variant="subtle" theme="red" :label="__('Delete')" @click="removeLevel(level)" />
          </div>
        </div>
      </div>
    </div>

    <div v-else class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5 text-p-sm text-ink-gray-5">
      {{ __('No agent levels have been added yet.') }}
    </div>

    <Dialog
      v-model="showDialog"
      :options="{
        title: dialogTitle,
        size: 'md',
        actions: [
          { label: __('Save'), variant: 'solid', onClick: saveLevel },
          { label: __('Cancel'), variant: 'subtle', onClick: () => (showDialog = false) },
        ],
      }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Level Name') }}</label>
            <input v-model="form.level_name" :class="inputClass" />
          </div>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Daily Rate') }}</label>
              <input v-model="form.daily_rate" type="number" min="0" step="0.01" :class="inputClass" />
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
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Sort Order') }}</label>
              <input v-model="form.sort_order" type="number" step="1" :class="inputClass" />
            </div>
            <label class="flex items-center gap-2 rounded border border-outline-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
              <input v-model="form.active" type="checkbox" class="h-4 w-4 rounded accent-blue-600" />
              {{ __('Active') }}
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
  level_name: '',
  daily_rate: '',
  currency: '',
  active: true,
  sort_order: 0,
  description: '',
})

const dialogTitle = computed(() =>
  editingName.value ? __('Edit Agent Level') : __('Add Agent Level'),
)

const levels = createResource({
  url: 'crm.api.redtra.billing.list_agent_levels',
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

function resetForm() {
  Object.assign(form, {
    level_name: '',
    daily_rate: '',
    currency: '',
    active: true,
    sort_order: 0,
    description: '',
  })
}

function openCreateDialog() {
  editingName.value = ''
  resetForm()
  showDialog.value = true
}

function openEditDialog(level) {
  editingName.value = level.name
  Object.assign(form, {
    level_name: level.level_name || '',
    daily_rate: level.daily_rate ?? '',
    currency: level.currency || '',
    active: Boolean(level.active),
    sort_order: level.sort_order ?? 0,
    description: level.description || '',
  })
  showDialog.value = true
}

async function saveLevel() {
  errorMessage.value = ''
  try {
    await call('crm.api.redtra.billing.save_agent_level', {
      name: editingName.value || null,
      data: JSON.stringify({
        level_name: form.level_name,
        daily_rate: Number(form.daily_rate || 0),
        currency: form.currency,
        active: form.active ? 1 : 0,
        sort_order: Number(form.sort_order || 0),
        description: form.description,
      }),
    })
    toast.success(__('Agent level saved successfully'))
    showDialog.value = false
    await levels.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

async function removeLevel(level) {
  if (!window.confirm(__('Delete agent level {0}?', [level.level_name]))) return

  try {
    await call('crm.api.redtra.billing.delete_agent_level', {
      name: level.name,
    })
    toast.success(__('Agent level deleted'))
    await levels.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}
</script>
