<template>
  <div
    v-if="document.doc?.is_featured"
    class="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
  >
    <div class="font-medium">
      {{ __('This property is currently featured.') }}
    </div>
    <div class="mt-1 text-amber-800">
      {{
        __(
          'Featured window: {0} to {1}',
          [
            formatDate(document.doc?.featured_from) || __('Not set'),
            formatDate(document.doc?.featured_until) || __('Not set'),
          ],
        )
      }}
    </div>
  </div>

  <div class="mb-5 rounded-lg border border-outline-gray-2 bg-surface-white p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-base font-semibold text-ink-gray-8">
        {{ __('Featured Details') }}
      </div>
      <Button
        :label="__('Refresh')"
        size="sm"
        variant="subtle"
        iconLeft="refresh-cw"
        :loading="featuredLogs.loading"
        @click="featuredLogs.reload()"
      />
    </div>

    <div v-if="featuredLogs.loading" class="py-3 text-sm text-ink-gray-5">
      {{ __('Loading featured logs...') }}
    </div>

    <div
      v-else-if="featuredLogRows.length"
      class="max-h-64 space-y-2 overflow-y-auto pr-1"
    >
      <div
        v-for="row in featuredLogRows"
        :key="row.name"
        class="rounded-md border border-outline-gray-2 px-3 py-2"
      >
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="eventTypeClass(row.event_type)"
            >
              {{ __(row.event_type || 'Updated') }}
            </span>
            <span class="text-xs text-ink-gray-6">
              {{ __(row.source || 'Desk') }}
            </span>
          </div>
          <span class="text-xs text-ink-gray-6">
            {{ formatDate(row.changed_on) }}
          </span>
        </div>
        <div class="mt-1 text-xs text-ink-gray-6">
          {{
            __(
              'From: {0}  •  Until: {1}',
              [formatDate(row.featured_from) || '-', formatDate(row.featured_until) || '-'],
            )
          }}
        </div>
        <div v-if="row.triggered_by" class="mt-1 text-xs text-ink-gray-6">
          {{ __('By: {0}', [row.triggered_by]) }}
        </div>
        <div v-if="row.notes" class="mt-1 text-sm text-ink-gray-8">
          {{ row.notes }}
        </div>
      </div>
    </div>

    <div v-else class="py-3 text-sm text-ink-gray-5">
      {{ __('No featured log entries found for this property.') }}
    </div>
  </div>

  <div
    class="my-3 flex items-center justify-between text-lg font-medium sm:mb-4 sm:mt-8"
  >
    <div class="flex h-8 items-center text-xl font-semibold text-ink-gray-8">
      {{ __('Data') }}
      <Badge
        v-if="document.isDirty"
        class="ml-3"
        :label="__('Not Saved')"
        theme="orange"
      />
    </div>
    <div class="flex gap-2">
      <Button
        :label="document.doc?.is_sold ? __('Unmark Sold') : __('Mark as Sold')"
        variant="subtle"
        :loading="availabilityLoading === 'is_sold'"
        @click="toggleAvailability('is_sold')"
      />
      <Button
        :label="document.doc?.is_rented ? __('Unmark Rented') : __('Mark as Rented')"
        variant="subtle"
        :loading="availabilityLoading === 'is_rented'"
        @click="toggleAvailability('is_rented')"
      />
      <Button
        :label="__('Save')"
        :disabled="!document.isDirty || saveLoading"
        variant="solid"
        :loading="saveLoading || document.save.loading"
        @click="saveChanges"
      />
    </div>
  </div>
  <div
    v-if="document.get.loading"
    class="flex flex-1 flex-col items-center justify-center gap-3 text-xl font-medium text-ink-gray-6"
  >
    <LoadingIndicator class="h-6 w-6" />
    <span>{{ __('Loading...') }}</span>
  </div>
  <div v-else class="pb-8">
    <FieldLayout
      v-if="tabs.length"
      :tabs="tabs"
      :data="document.doc"
      doctype="Property"
    >
      <template #field="{ field }">
        <div v-if="field.fieldname === 'trakheesi_qr_code'" class="space-y-2">
          <label class="text-sm font-medium text-ink-gray-5">{{ __(field.label) }}</label>
          <div v-if="document.doc.trakheesi_qr_code" class="relative group w-32 h-32 rounded border border-outline-gray-2 overflow-hidden bg-white p-1">
            <img :src="document.doc.trakheesi_qr_code" class="w-full h-full object-contain" />
          </div>
          <ImageUploader
            :image-url="document.doc.trakheesi_qr_code"
            @upload="(url) => document.doc.trakheesi_qr_code = url"
            @remove="document.doc.trakheesi_qr_code = ''"
          />
        </div>
      </template>
    </FieldLayout>
  </div>
</template>

<script setup>
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { useDocument } from '@/data/document'
import { getMeta } from '@/stores/meta'
import { formatDate } from '@/utils'
import { Badge, Button, call, createResource, toast } from 'frappe-ui'
import { buildPropertyDataTabs, normalizePropertyDoc } from '@/utils/propertyFields'
import { computed, watch, getCurrentInstance, ref } from 'vue'

const props = defineProps({
  docname: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['beforeSave', 'afterSave'])

const instance = getCurrentInstance()
const attrs = instance?.vnode?.props ?? {}

const { getFields } = getMeta('Property')
const { document } = useDocument('Property', props.docname)
const availabilityLoading = ref('')
const saveLoading = ref(false)

const tabs = computed(() => buildPropertyDataTabs(getFields(), document.doc || {}))
const featuredLogRows = computed(() => featuredLogs.data || [])

const featuredLogs = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Property Featured Log',
    fields: [
      'name',
      'event_type',
      'source',
      'changed_on',
      'triggered_by',
      'featured_from',
      'featured_until',
      'notes',
    ],
    filters: {
      property: props.docname,
    },
    order_by: 'changed_on desc',
    limit_page_length: 50,
  },
  auto: true,
})

watch(
  () => [
    document.doc?.listing_type,
    document.doc?.property_category,
    document.doc?.is_featured,
  ],
  () => {
    normalizePropertyDoc(document.doc)
  },
)

watch(
  () => document.doc,
  (newValue, oldValue) => {
    if (!oldValue) return
    if (newValue && oldValue) {
      // Use frappe-ui's internal dirty tracking if available, 
      // but keep this for custom field normalization tracking
      const isDirty = JSON.stringify(newValue) !== JSON.stringify(document.originalDoc)
      
      // Only set if it actually changed to avoid redundant re-renders
      if (document.isDirty !== isDirty) {
        document.isDirty = isDirty
      }
      
      if (isDirty) {
        document.save.loading = false
      }
    }
  },
  { deep: true },
)

watch(
  () => document.save.loading,
  (loading) => {
    if (!loading && saveLoading.value) {
      saveLoading.value = false
    }
  },
)

watch(
  () => document.save.success,
  (success) => {
    if (success) {
      saveLoading.value = false
      document.isDirty = false
      featuredLogs.reload()
    }
  }
)

function eventTypeClass(eventType) {
  if (eventType === 'Activated') return 'bg-green-100 text-green-800'
  if (eventType === 'Deactivated') return 'bg-red-100 text-red-800'
  if (eventType === 'Expired') return 'bg-orange-100 text-orange-800'
  return 'bg-blue-100 text-blue-800'
}

async function toggleAvailability(fieldname) {
  if (!document.doc?.name || availabilityLoading.value) return

  const nextValue = document.doc[fieldname] ? 0 : 1
  const previousValue = document.doc[fieldname]
  availabilityLoading.value = fieldname
  document.doc[fieldname] = nextValue

  try {
    await call('frappe.client.set_value', {
      doctype: 'Property',
      name: document.doc.name,
      fieldname: {
        [fieldname]: nextValue,
      },
    })

    if (document.originalDoc) {
      document.originalDoc[fieldname] = nextValue
    }
    toast.success(
      nextValue
        ? __('Property marked as {0}.', [fieldname === 'is_sold' ? __('sold') : __('rented')])
        : __('Property status updated.'),
    )
  } catch (error) {
    document.doc[fieldname] = previousValue
    toast.error(error?.messages?.[0] || error?.message || __('Failed to update property status.'))
  } finally {
    availabilityLoading.value = ''
  }
}

function saveChanges() {
  if (!document.isDirty || saveLoading.value) return

  normalizePropertyDoc(document.doc)

  const updatedDoc = { ...document.doc }
  const oldDoc = { ...document.originalDoc }

  const changes = Object.keys(updatedDoc).reduce((acc, key) => {
    if (JSON.stringify(updatedDoc[key]) !== JSON.stringify(oldDoc[key])) {
      acc[key] = updatedDoc[key]
    }
    return acc
  }, {})

  const hasListener = attrs.onBeforeSave !== undefined

  saveLoading.value = true

  if (hasListener) {
    emit('beforeSave', changes)
    queueMicrotask(() => {
      if (!document.save.loading) {
        saveLoading.value = false
      }
    })
    return
  }

  document.save.submit(null, {
    onSuccess: () => {
      saveLoading.value = false
      emit('afterSave', changes)
    },
    onError: () => {
      saveLoading.value = false
    },
  })
}
</script>
