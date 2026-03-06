<template>
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
    <div class="flex gap-1">
      <Button
        :label="__('Save')"
        :disabled="!document.isDirty"
        variant="solid"
        :loading="document.save.loading"
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
    />
  </div>
</template>

<script setup>
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import LoadingIndicator from '@/components/Icons/LoadingIndicator.vue'
import { useDocument } from '@/data/document'
import { getMeta } from '@/stores/meta'
import { Badge } from 'frappe-ui'
import { buildPropertyDataTabs, normalizePropertyDoc } from '@/utils/propertyFields'
import { computed, watch, getCurrentInstance } from 'vue'

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

const tabs = computed(() => buildPropertyDataTabs(getFields(), document.doc || {}))

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
      const isDirty =
        JSON.stringify(newValue) !== JSON.stringify(document.originalDoc)
      document.isDirty = isDirty
      if (isDirty) {
        document.save.loading = false
      }
    }
  },
  { deep: true },
)

function saveChanges() {
  if (!document.isDirty) return

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

  if (hasListener) {
    emit('beforeSave', changes)
    return
  }

  document.save.submit(null, {
    onSuccess: () => emit('afterSave', changes),
  })
}
</script>
