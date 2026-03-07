<template>
  <Dialog v-model="show" :options="{ size: '3xl' }">
    <template #body>
      <div class="bg-surface-modal px-4 pb-6 pt-5 sm:px-6">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
              {{ __('Create Property') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="ghost" class="w-7" @click="show = false" icon="x" />
          </div>
        </div>
        <div>
          <FieldLayout
            v-if="tabs.length"
            :tabs="tabs"
            :data="property.doc"
            doctype="Property"
          />
          <ErrorMessage class="mt-4" v-if="error" :message="__(error)" />
        </div>
      </div>
      <div class="px-4 pb-7 pt-4 sm:px-6">
        <div class="flex flex-row-reverse gap-2">
          <Button
            variant="solid"
            :label="__('Create')"
            :loading="isPropertyCreating"
            @click="createNewProperty"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import { usersStore } from '@/stores/users'
import { getMeta } from '@/stores/meta'
import { capture } from '@/telemetry'
import { createResource } from 'frappe-ui'
import { useDocument } from '@/data/document'
import {
  buildPropertyQuickEntryTabs,
  normalizePropertyDoc,
  validatePropertyDoc,
} from '@/utils/propertyFields'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  defaults: Object,
})

const { getUser } = usersStore()
const { getFields } = getMeta('Property')

const show = defineModel()
const router = useRouter()
const error = ref(null)
const isPropertyCreating = ref(false)

const { document: property, triggerOnBeforeCreate } = useDocument('Property')

const tabs = computed(() => buildPropertyQuickEntryTabs(getFields(), property.doc || {}))

const createProperty = createResource({
  url: 'frappe.client.insert',
})

watch(
  () => [
    property.doc?.listing_type,
    property.doc?.property_category,
    property.doc?.is_featured,
  ],
  () => normalizePropertyDoc(property.doc),
)

async function createNewProperty() {
  normalizePropertyDoc(property.doc)
  await triggerOnBeforeCreate?.()

  createProperty.submit(
    {
      doc: {
        doctype: 'Property',
        ...property.doc,
      },
    },
    {
      validate() {
        error.value = null
        const validationError = validatePropertyDoc(property.doc)
        if (validationError) {
          error.value = validationError
          return validationError
        }
        isPropertyCreating.value = true
      },
      onSuccess(data) {
        capture('property_created')
        isPropertyCreating.value = false
        show.value = false
        router.push({ name: 'Property', params: { propertyId: data.name } })
      },
      onError(err) {
        isPropertyCreating.value = false
        if (!err.messages) {
          error.value = err.message
          return
        }
        error.value = err.messages.join('\n')
      },
    },
  )
}

onMounted(() => {
  property.doc = {}
  Object.assign(property.doc, props.defaults)

  if (!property.doc?.agent) {
    property.doc.agent = getUser().name
  }
  if (!property.doc?.status) {
    property.doc.status = 'Draft'
  }
  if (!property.doc?.currency) {
    property.doc.currency = window.sysdefaults?.currency || 'USD'
  }
  normalizePropertyDoc(property.doc)
})
</script>
