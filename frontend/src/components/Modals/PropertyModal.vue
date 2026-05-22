<template>
  <Dialog v-model="show" :options="{ size: '4xl' }">
    <template #body>
      <div class="bg-surface-modal px-4 py-5 sm:px-6 rounded-t-xl">
        <div class="mb-6 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <h3 class="text-xl font-semibold leading-6 text-ink-gray-9">
              {{ __('Add new property') }}
            </h3>
            <Badge theme="orange" size="sm">Draft</Badge>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="subtle" @click="show = false">{{ __('Cancel') }}</Button>
            <Button variant="solid" :loading="isPropertyCreating" @click="createNewProperty">{{ __('Save & submit') }}</Button>
          </div>
        </div>

        <div class="mb-6">
          <div class="text-sm text-ink-gray-6 mb-3 font-medium">Listing type</div>
          <div class="flex gap-4">
            <button
              class="flex-1 flex flex-col justify-center rounded-lg border p-4 text-left transition-colors cursor-pointer"
              :class="
                property.doc.listing_type === 'Buy' && property.doc.completion_status !== 'Off-Plan'
                  ? 'border-ink-blue-3 bg-surface-blue-2 ring-1 ring-ink-blue-3'
                  : 'border-outline-gray-modals hover:bg-surface-gray-2'
              "
              @click="setListingType('Buy', 'Ready')"
            >
              <div class="font-medium" :class="property.doc.listing_type === 'Buy' && property.doc.completion_status !== 'Off-Plan' ? 'text-ink-blue-5' : 'text-ink-gray-9'">Buy</div>
              <div class="text-sm text-ink-gray-5">Ready property</div>
            </button>
            <button
              class="flex-1 flex flex-col justify-center rounded-lg border p-4 text-left transition-colors cursor-pointer"
              :class="
                property.doc.listing_type === 'Rent'
                  ? 'border-ink-blue-3 bg-surface-blue-2 ring-1 ring-ink-blue-3'
                  : 'border-outline-gray-modals hover:bg-surface-gray-2'
              "
              @click="setListingType('Rent', 'Ready')"
            >
              <div class="font-medium" :class="property.doc.listing_type === 'Rent' ? 'text-ink-blue-5' : 'text-ink-gray-9'">Rent</div>
              <div class="text-sm text-ink-gray-5">Lease listing</div>
            </button>
            <button
              class="flex-1 flex flex-col justify-center rounded-lg border p-4 text-left transition-colors cursor-pointer"
              :class="
                property.doc.listing_type === 'Buy' && property.doc.completion_status === 'Off-Plan'
                  ? 'border-ink-blue-3 bg-surface-blue-2 ring-1 ring-ink-blue-3'
                  : 'border-outline-gray-modals hover:bg-surface-gray-2'
              "
              @click="setListingType('Buy', 'Off-Plan')"
            >
              <div class="font-medium" :class="property.doc.listing_type === 'Buy' && property.doc.completion_status === 'Off-Plan' ? 'text-ink-blue-5' : 'text-ink-gray-9'">Off plan</div>
              <div class="text-sm text-ink-gray-5">+ payment plan</div>
            </button>
          </div>
        </div>

        <div
          v-if="property.doc?.is_featured"
          class="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
        >
          {{
            __(
              'Featured listing is enabled. Additional charges apply for featured properties.',
            )
          }}
        </div>

        <div class="border border-outline-gray-modals rounded-lg bg-surface-modal overflow-hidden shadow-sm">
          <Tabs v-model="tabIndex" :tabs="tabs" as="div">
            <template #tab-panel="{ tab }">
              <div class="p-4 sm:p-5 overflow-y-auto min-h-[300px] max-h-[50vh]">
                <template v-if="tab.name === 'amenities_tab'">
                  <div class="mb-6 pb-6 border-b border-outline-gray-modals">
                    <div class="flex items-center justify-between mb-3">
                      <div class="text-sm font-medium text-ink-gray-6">Quick add amenities</div>
                    </div>
                    <div class="flex flex-wrap gap-2 mb-4">
                       <button
                          v-for="amenity in quickAmenities" :key="amenity"
                          class="rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
                          :class="isAmenitySelected(amenity) ? 'bg-ink-blue-5 text-white' : 'bg-surface-gray-2 hover:bg-surface-gray-3 text-ink-gray-8'"
                          @click="toggleQuickAmenity(amenity)"
                       >
                         {{ isAmenitySelected(amenity) ? '✓ ' : '+ ' }}{{ amenity }}
                       </button>
                    </div>
                    <div class="flex items-center gap-2 max-w-sm">
                      <FormControl
                        type="text"
                        placeholder="Add custom amenity..."
                        v-model="customAmenityInput"
                        @keydown.enter.prevent="addCustomAmenity"
                        class="flex-1"
                      />
                      <Button variant="outline" @click="addCustomAmenity">Add</Button>
                    </div>
                  </div>
                  <div class="mb-6" v-if="property.doc.amenities?.length">
                    <div class="text-sm font-medium text-ink-gray-6 mb-3">Selected amenities</div>
                    <div class="flex flex-wrap gap-2">
                      <Badge
                        v-for="(a, idx) in property.doc.amenities"
                        :key="idx"
                        theme="blue"
                        size="md"
                        closable
                        @close="removeAmenity(idx)"
                      >
                        {{ a.amenity_name }}
                      </Badge>
                    </div>
                  </div>
                </template>
                <template v-if="tab.name === 'media_tab'">
                  <div class="sections overflow-hidden">
                    <Section v-for="section in tab.sections" :key="section.name" :section="section" :data-name="section.name">
                      <template #field="{ field }">
                         <div v-if="field.fieldname === 'description'" class="space-y-1.5">
                            <label class="text-sm font-medium text-ink-gray-6">{{ __(field.label) }}</label>
                            <FormControl
                              type="textarea"
                              :placeholder="__(field.placeholder)"
                              v-model="property.doc.description"
                              rows="6"
                            />
                         </div>
                         <div v-else-if="['featured_from', 'featured_until'].includes(field.fieldname)" class="space-y-1.5">
                            <label class="text-sm font-medium text-ink-gray-6">
                              {{ __(field.label) }}
                            </label>
                            <input
                              type="datetime-local"
                              class="w-full rounded-md border border-outline-gray-3 bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none"
                              :value="toDateTimeLocalValue(property.doc[field.fieldname])"
                              @input="(event) => triggerOnChange(field.fieldname, fromDateTimeLocalValue(event.target.value))"
                            />
                            <div v-if="fieldErrors[field.fieldname]" class="mt-1 text-xs text-red-500">
                              {{ __(fieldErrors[field.fieldname]) }}
                            </div>
                         </div>
                         <div v-else-if="field.fieldname === 'trakheesi_qr_code'" class="space-y-2">
                            <label class="text-sm font-medium text-ink-gray-6">{{ __(field.label) }}</label>
                            <div v-if="property.doc.trakheesi_qr_code" class="relative group w-32 h-32 rounded border border-outline-gray-2 overflow-hidden bg-white p-1">
                               <img :src="property.doc.trakheesi_qr_code" class="w-full h-full object-contain" />
                               <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                  <Button variant="ghost" size="sm" class="text-white hover:text-red-400" icon="trash-2" @click="property.doc.trakheesi_qr_code = ''" />
                               </div>
                            </div>
                            <ImageUploader
                               :image-url="property.doc.trakheesi_qr_code"
                               @upload="(url) => triggerOnChange('trakheesi_qr_code', url)"
                               @remove="triggerOnChange('trakheesi_qr_code', '')"
                            />
                         </div>
                      </template>
                    </Section>
                  </div>
                </template>
                <template v-else-if="tab.name === 'offplan_details_tab'">
                  <div class="bg-surface-blue-2 text-ink-blue-5 text-sm font-medium px-4 py-3 rounded-lg mb-4">
                    Required for off-plan listings
                  </div>
                  <div class="sections overflow-hidden">
                    <Section v-for="section in tab.sections" :key="section.name" :section="section" :data-name="section.name" />
                  </div>
                </template>
                <template v-else>
                  <div class="sections overflow-hidden">
                    <Section v-for="section in tab.sections" :key="section.name" :section="section" :data-name="section.name" />
                  </div>
                </template>

                <ErrorMessage class="mt-4" v-if="error" :message="__(error)" />
              </div>
            </template>
          </Tabs>

          <div class="flex items-center justify-between border-t border-outline-gray-modals px-5 py-4 bg-surface-gray-2">
            <div class="text-sm text-ink-gray-5 font-medium">
              Tab {{ tabIndex + 1 }} of {{ tabs.length }}
            </div>
            <div class="flex items-center gap-2">
              <Button 
                variant="subtle" 
                @click="tabIndex--" 
                :disabled="tabIndex === 0"
                iconLeft="arrow-left"
              >
                Back
              </Button>
              <Button 
                v-if="tabIndex < tabs.length - 1"
                variant="solid" 
                @click="tabIndex++"
              >
                Next &rarr;
              </Button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import Section from '@/components/FieldLayout/Section.vue'
import { Badge, Tabs, Button, ErrorMessage, Dialog, FormControl, toast } from 'frappe-ui'
import { usersStore } from '@/stores/users'
import { getMeta } from '@/stores/meta'
import { capture } from '@/telemetry'
import { createResource } from 'frappe-ui'
import { useDocument } from '@/data/document'
import {
  buildPropertyQuickEntryTabs,
  normalizePropertyDoc,
  validatePropertyDoc,
  getFieldErrors,
  STANDARD_AMENITIES
} from '@/utils/propertyFields'
import { agentStore } from '@/stores/agent'
import { computed, onMounted, ref, watch, provide } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  defaults: Object,
  propertyId: String,
})

const { getUser } = usersStore()
const { getFields } = getMeta('Property')

const show = defineModel()
const router = useRouter()
const error = ref(null)
const fieldErrors = ref({})
const isPropertyCreating = ref(false)
const customAmenityInput = ref('')

const tabIndex = ref(0)
const hasTabs = computed(() => true)
const { agentResource } = agentStore()

const {
  document: property,
  triggerOnChange,
  triggerOnBeforeCreate,
} = useDocument('Property', props.propertyId)

provide('data', computed(() => property.doc))
provide('fieldErrors', fieldErrors)
provide('hasTabs', hasTabs)
provide('doctype', 'Property')
provide('preview', ref(false))
provide('isGridRow', ref(false))
provide('triggerOnChange', triggerOnChange)

const tabs = computed(() => buildPropertyQuickEntryTabs(getFields(), property.doc || {}))

const amenitiesResource = createResource({
  url: 'frappe.client.get_list',
  params: {
    doctype: 'Amenity',
    fields: ['name', 'amenity_name', 'icon'],
    limit: 50,
  },
  auto: true,
})

const quickAmenities = computed(() => {
  return amenitiesResource.data?.map(a => a.amenity_name) || STANDARD_AMENITIES
})

const createProperty = createResource({
  url: 'frappe.client.insert',
})

onMounted(() => {
  if (!props.propertyId && property.doc) {
    property.doc.country = 'United Arab Emirates'
    property.doc.status = 'Draft'
    property.doc.primary_image = ''
    property.doc.amenities = []
  }
})

function setListingType(listingType, completionStatus) {
  if (!property.doc) return
  property.doc.listing_type = listingType
  property.doc.completion_status = completionStatus
  
  if (completionStatus !== 'Off-Plan') {
    if (tabIndex.value > tabs.value.length - 1) {
      tabIndex.value = Math.max(0, tabs.value.length - 1)
    }
  }
}

function toDateTimeLocalValue(value) {
  if (!value) return ''
  return String(value).replace(' ', 'T').slice(0, 16)
}

function fromDateTimeLocalValue(value) {
  if (!value) return ''
  const normalized = String(value).replace('T', ' ')
  return normalized.length === 16 ? `${normalized}:00` : normalized
}

async function addCustomAmenity() {
  const txt = customAmenityInput.value.trim()
  if (!txt || !property.doc) return

  if (!property.doc.amenities) {
    property.doc.amenities = []
  }

  // Check if already added
  if (property.doc.amenities.find(a => a.amenity_name === txt)) {
    customAmenityInput.value = ''
    return
  }

  // Ensure the Amenity record exists before adding
  await ensureAmenityExists(txt)

  property.doc.amenities = [...property.doc.amenities, { amenity_name: txt }]
  customAmenityInput.value = ''
}

function isAmenitySelected(amenityName) {
  return property.doc?.amenities?.find(a => a.amenity_name === amenityName)
}

async function toggleQuickAmenity(amenityName) {
  if (!property.doc) return
  if (!property.doc.amenities) property.doc.amenities = []
  
  const idx = property.doc.amenities.findIndex(a => a.amenity_name === amenityName)
  if (idx > -1) {
    property.doc.amenities = property.doc.amenities.filter((_, i) => i !== idx)
  } else {
    await ensureAmenityExists(amenityName)
    property.doc.amenities = [...property.doc.amenities, { amenity_name: amenityName }]
  }
}

function removeAmenity(index) {
  if (property.doc?.amenities) {
    property.doc.amenities = property.doc.amenities.filter((_, i) => i !== index)
  }
}

// Ensure the Amenity record exists in the Amenity doctype (auto-create if missing)
async function ensureAmenityExists(amenityName) {
  try {
    await createResource({
      url: 'frappe.client.insert_many',
    }).submit({
      docs: [{ doctype: 'Amenity', amenity_name: amenityName }],
    })
  } catch {
    // Ignore duplicate errors – record already exists
  }
}

watch(
  () => [
    property.doc?.listing_type,
    property.doc?.property_category,
    property.doc?.is_featured,
  ],
  () => normalizePropertyDoc(property.doc),
)

watch(
  () => agentResource.data,
  (data) => {
    if (data?.name && !property.doc?.agent) {
      property.doc.agent = data.name
    }
  },
  { immediate: true }
)

watch(
  () => property.doc,
  (doc) => {
    if (doc) {
      fieldErrors.value = getFieldErrors(doc)
    }
  },
  { deep: true, immediate: true }
)

async function createNewProperty() {
  normalizePropertyDoc(property.doc)
  await triggerOnBeforeCreate?.()

  // Save & submit: set status to Active or Under Verification
  if (property.doc.status === 'Draft') {
    property.doc.status = 'Under Verification'
  }

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
          toast.error(validationError)
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
        let msg = err.message
        if (err.messages) {
          msg = err.messages.join('\n')
        }
        toast.error(msg)
      },
    },
  )
}

onMounted(() => {
  property.doc = {}
  Object.assign(property.doc, props.defaults)

  if (!property.doc?.agent) {
    // Use the current agent's DLD ID (name field), not the user email
    const agentName = agentResource?.data?.name
    if (agentName) {
      property.doc.agent = agentName
    }
  }
  if (!property.doc?.status) {
    property.doc.status = 'Draft'
  }
  if (!property.doc?.currency) {
    property.doc.currency = window.sysdefaults?.currency || 'AED'
  }
  if (!property.doc?.country) {
    property.doc.country = 'United Arab Emirates'
  }
  if (!property.doc?.listing_type) {
    setListingType('Buy', 'Ready')
  }
  
  normalizePropertyDoc(property.doc)
})
</script>
