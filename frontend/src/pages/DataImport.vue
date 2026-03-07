<template>
  <DataImport
    :doctype="route.params.doctype"
    :importName="route.params.importName"
    :doctypeMap="doctypeMap"
  />
</template>

<script setup>
import { usePageMeta } from 'frappe-ui'
import { DataImport } from 'frappe-ui/frappe'
import { sessionStore } from '@/stores/session'
import { useRoute, useRouter } from 'vue-router'
import { inject, onMounted } from 'vue'

const { user } = sessionStore()
const route = useRoute()
const router = useRouter()

const doctypeMap = {
  'Property': {
    title: 'Properties',
    listRoute: '/properties',
  },
  'CRM Lead': {
    title: 'Leads',
    listRoute: '/leads',
  },
  'CRM Deal': {
    title: 'Deals',
    listRoute: '/deals',
  },
}

usePageMeta(() => {
  return {
    title: 'Data Import',
  }
})
</script>
