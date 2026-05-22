<template>
  <FrappeDataImport
    :key="refreshKey"
    :doctype="route.params.doctype"
    :importName="route.params.importName"
    :doctypeMap="doctypeMap"
  />
</template>

<script setup>
import { usePageMeta } from 'frappe-ui'
import { globalStore } from '@/stores/global'
import FrappeDataImport from '@/components/DataImport/FrappeDataImport.vue'
import { useRoute } from 'vue-router'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const { $socket } = globalStore()
const route = useRoute()
const refreshKey = ref(0)

const doctypeMap = {
  'Property': {
    title: 'Properties',
    listRoute: '/crm/properties',
    pageRoute: '/crm/properties/docname',
  },
  'CRM Lead': {
    title: 'Leads',
    listRoute: '/crm/leads',
    pageRoute: '/crm/leads/docname',
  },
  'CRM Deal': {
    title: 'Deals',
    listRoute: '/crm/deals',
    pageRoute: '/crm/deals/docname',
  },
}

usePageMeta(() => {
  return {
    title: 'Data Import',
  }
})

function handleDataImportRefresh(data) {
  if (!data?.data_import) return

  if (
    !route.params.importName ||
    route.params.importName === data.data_import
  ) {
    refreshKey.value += 1
  }
}

onMounted(() => {
  $socket?.off('data_import_refresh', handleDataImportRefresh)
  $socket?.on('data_import_refresh', handleDataImportRefresh)
})

onBeforeUnmount(() => {
  $socket?.off('data_import_refresh', handleDataImportRefresh)
})
</script>
