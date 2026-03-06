<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <div class="flex items-center justify-between border-b px-4 py-2">
      <div class="text-sm font-medium text-ink-gray-6">
        {{ __('Property Sidebar') }}
      </div>
      <Button
        variant="ghost"
        icon="settings-2"
        :label="__('Customize')"
        @click="draftVisibleSections = [...visibleSections]; showCustomizer = true"
      />
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto">
      <SidePanelLayout
        class="h-full"
        :sections="sections"
        doctype="Property"
        :docname="docname"
        @afterFieldChange="(data) => emit('afterFieldChange', data)"
      />
    </div>
  </div>
  <Dialog v-model="showCustomizer" :options="{ size: 'xl' }">
    <template #body-title>
      <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
        {{ __('Customize Property Sidebar') }}
      </h3>
    </template>
    <template #body-content>
      <div class="space-y-3">
        <div class="text-sm text-ink-gray-6">
          {{ __('Choose which sections should stay visible in the Property sidebar.') }}
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
          <label
            v-for="section in sidebarSectionOptions"
            :key="section.name"
            class="flex items-center gap-3 rounded border px-3 py-2"
          >
            <FormControl
              type="checkbox"
              :modelValue="draftVisibleSections.includes(section.name)"
              @change="toggleSection(section.name, $event.target.checked)"
            />
            <span class="text-base text-ink-gray-8">{{ __(section.label) }}</span>
          </label>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex items-center justify-end gap-2">
        <Button :label="__('Reset')" @click="resetSidebar" />
        <Button
          :label="__('Save')"
          variant="solid"
          :loading="saving"
          @click="saveSidebarSections"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import SidePanelLayout from '@/components/SidePanelLayout.vue'
import { getMeta } from '@/stores/meta'
import {
  PROPERTY_SIDEBAR_SETTINGS_KEY,
  buildPropertySidebarSections,
  getPropertySidebarSectionNames,
  getPropertySidebarSectionOptions,
} from '@/utils/propertyFields'
import { Dialog, FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
  docname: {
    type: String,
    required: true,
  },
  doc: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['afterFieldChange'])

const { getFields, userSettings, saveUserSettings } = getMeta('Property')

const saving = ref(false)
const showCustomizer = ref(false)
const sidebarSectionOptions = getPropertySidebarSectionOptions()
const defaultVisibleSections = getPropertySidebarSectionNames()
const draftVisibleSections = ref([...defaultVisibleSections])

const visibleSections = computed(() => {
  return (
    userSettings.Property?.[PROPERTY_SIDEBAR_SETTINGS_KEY]?.Property
      ?.visibleSections || defaultVisibleSections
  )
})

const sections = computed(() => {
  return buildPropertySidebarSections(getFields(), {
    doc: props.doc,
    visibleSections: visibleSections.value,
  })
})

function toggleSection(sectionName, checked) {
  if (checked) {
    draftVisibleSections.value = [...new Set([...draftVisibleSections.value, sectionName])]
    return
  }

  draftVisibleSections.value = draftVisibleSections.value.filter(
    (section) => section !== sectionName,
  )
}

function resetSidebar() {
  draftVisibleSections.value = [...defaultVisibleSections]
}

function saveSidebarSections() {
  saving.value = true

  let visible = draftVisibleSections.value.length
    ? draftVisibleSections.value
    : [...defaultVisibleSections]

  saveUserSettings(
    'Property',
    PROPERTY_SIDEBAR_SETTINGS_KEY,
    { visibleSections: visible },
    () => {
      saving.value = false
      showCustomizer.value = false
    },
  )
}
</script>
