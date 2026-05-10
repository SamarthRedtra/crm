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
  <div
    v-if="hasFeaturedOverdues"
    class="mx-4 mt-3 flex items-center justify-between rounded-lg border border-amber-300 bg-amber-50 px-4 py-3"
  >
    <div class="text-sm text-amber-900">
      {{
        __('{0} featured listing invoice(s) are overdue · Total {1} {2}', [
          featuredOverdues?.count || 0,
          featuredOverdues?.currency || 'AED',
          formatAmount(featuredOverdues?.total_overdue || 0),
        ])
      }}
    </div>
    <Button variant="solid" size="sm" @click="showFeaturedPaymentsModal = true">
      {{ __('Pay now') }}
    </Button>
  </div>
  <PropertiesListView
    ref="propertiesListView"
    v-if="properties.data && rows.length"
    v-model="properties.data.page_length_count"
    v-model:list="properties"
    :rows="rows"
    :columns="properties.data.columns"
    :onFeaturePay="openFeatureModalFromSelections"
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
    @selectionsChanged="handleSelectionsChanged"
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
  <FeatureListingsModal
    v-if="showFeatureListingsModal"
    v-model="showFeatureListingsModal"
    :selectedProperties="featureModalProperties"
    @checkoutCreated="showFeatureListingsModal = false"
  />
  <FeaturedPaymentsModal
    v-if="showFeaturedPaymentsModal"
    v-model="showFeaturedPaymentsModal"
    :overdues="featuredOverdues"
  />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import PropertiesIcon from '@/components/Icons/NoteIcon.vue' // Placeholder
import LayoutHeader from '@/components/LayoutHeader.vue'
import PropertiesListView from '@/components/ListViews/PropertiesListView.vue'
import FeatureListingsModal from '@/components/Modals/FeatureListingsModal.vue'
import FeaturedPaymentsModal from '@/components/Modals/FeaturedPaymentsModal.vue'
import PropertyModal from '@/components/Modals/PropertyModal.vue'
import ViewControls from '@/components/ViewControls.vue'
import { getMeta } from '@/stores/meta'
import { statusesStore } from '@/stores/statuses'
import { formatDate, timeAgo } from '@/utils'
import { call, createResource, toast } from 'frappe-ui'
import { ref, computed, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const { getFormattedCurrency } = getMeta('Property')
const { getPropertyStatus } = statusesStore()

const router = useRouter()
const route = useRoute()

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
const showFeatureListingsModal = ref(false)
const showFeaturedPaymentsModal = ref(false)
const featureModalProperties = ref([])

const featuredOverduesResource = createResource({
  url: 'crm.api.redtra.billing.list_featured_overdues',
  auto: true,
  onError() {
    // Permissions can vary by role; keep UI silent for non-billing users.
  },
})

const featuredOverdues = computed(() => featuredOverduesResource.data || {})
const hasFeaturedOverdues = computed(() => Number(featuredOverdues.value?.count || 0) > 0)

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

function handleSelectionsChanged(selections) {
  viewControls.value?.updateSelections(selections)
}

function openFeatureModalFromSelections(selections) {
  const selectedNames = Array.from(selections || [])
  featureModalProperties.value = rows.value
    .filter((row) => selectedNames.includes(row.name))
    .map((row) => ({
      name: row.name,
      title: row.title,
    }))
  if (!featureModalProperties.value.length) {
    toast.error(__('Please select at least one property.'))
    return
  }
  showFeatureListingsModal.value = true
}

async function handleFeaturedCheckoutReturn() {
  const status = route.query.featured_purchase
  const sessionId = route.query.session_id
  if (!status) return
  if (status === 'success' && sessionId) {
    try {
      await call('crm.api.redtra.billing.complete_featured_checkout', {
        session_id: sessionId,
      })
      toast.success(__('Featured purchase completed successfully.'))
      properties.value?.reload?.()
      await featuredOverduesResource.reload()
    } catch (error) {
      toast.error(error?.messages?.[0] || error?.message)
    }
  } else if (status === 'cancel') {
    toast.info(__('Featured purchase was cancelled.'))
  }

  const nextQuery = { ...route.query }
  delete nextQuery.featured_purchase
  delete nextQuery.session_id
  router.replace({ path: route.path, query: nextQuery })
}

function formatAmount(value) {
  return Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

watch(
  () => route.query.featured_purchase,
  () => handleFeaturedCheckoutReturn(),
  { immediate: true },
)
</script>
