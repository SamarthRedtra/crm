<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Properties" />
    </template>
    <template #right-header>
      <Button
        variant="ghost"
        :label="__('Import Properties')"
        iconLeft="upload"
        @click="goToImport"
      />
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="showPropertyModal = true"
      />
    </template>
  </LayoutHeader>
  <ViewControls
    ref="viewControls"
    v-model="properties"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="Property"
    :options="{
      allowedViews: ['list'],
    }"
  />
  <PropertiesListView
    ref="propertiesListView"
    v-if="properties.data && rows.length"
    v-model="properties.data.page_length_count"
    v-model:list="properties"
    :rows="rows"
    :columns="properties.data.columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: properties.data.row_count,
      totalCount: properties.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @applyFilter="(data) => viewControls.applyFilter(data)"
    @selectionsChanged="
      (selections) => viewControls.updateSelections(selections)
    "
  />
  <div v-else-if="properties.data" class="flex h-full items-center justify-center">
    <div
      class="flex flex-col items-center gap-3 text-xl font-medium text-ink-gray-4"
    >
      <PropertiesIcon class="h-10 w-10" />
      <span>{{ __('No {0} Found', [__('Properties')]) }}</span>
      <Button
        :label="__('Create')"
        iconLeft="plus"
        @click="showPropertyModal = true"
      />
      <Button
        variant="ghost"
        :label="__('Import')"
        iconLeft="upload"
        @click="goToImport"
      />
    </div>
  </div>
  <PropertyModal
    v-if="showPropertyModal"
    v-model="showPropertyModal"
    :defaults="defaults"
  />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import PropertiesIcon from '@/components/Icons/NoteIcon.vue' // Placeholder
import LayoutHeader from '@/components/LayoutHeader.vue'
import PropertiesListView from '@/components/ListViews/PropertiesListView.vue'
import PropertyModal from '@/components/Modals/PropertyModal.vue'
import ViewControls from '@/components/ViewControls.vue'
import { getMeta } from '@/stores/meta'
import { statusesStore } from '@/stores/statuses'
import { formatDate, timeAgo } from '@/utils'
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

const { getFormattedCurrency } = getMeta('Property')
const { getPropertyStatus } = statusesStore()

const router = useRouter()

function goToImport() {
  router.push({ name: 'Data Import', params: { doctype: 'Property' } })
}

const propertiesListView = ref(null)
const showPropertyModal = ref(false)

const defaults = reactive({})

const properties = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (!properties.value?.data?.data || !properties.value?.data?.rows) return []
  return parseRows(properties.value?.data.data, properties.value.data.columns)
})

function parseRows(rows, columns = []) {
  if (!rows) return []
  return rows.map((property) => {
    let _rows = {}
    const rowFields = properties.value?.data?.rows || []
    rowFields.forEach((row) => {
      _rows[row] = property[row]

      let field = columns?.find((col) => col.key == row)
      let fieldType = field?.type

      if (fieldType && ['Date', 'Datetime'].includes(fieldType) && !['modified', 'creation'].includes(row)) {
        _rows[row] = formatDate(property[row], '', true, fieldType == 'Datetime')
      }

      if (fieldType && fieldType == 'Currency') {
        _rows[row] = getFormattedCurrency(row, property)
      }

      if (['modified', 'creation'].includes(row)) {
        _rows[row] = {
          label: formatDate(property[row]),
          timeAgo: property[row] ? __(timeAgo(property[row])) : '',
        }
      } else if (row === 'status') {
        _rows[row] = {
          label: property.status,
          color: getPropertyStatus(property.status)?.color,
        }
      }
    })
    return _rows
  })
}
</script>
