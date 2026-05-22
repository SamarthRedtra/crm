<template>
  <header
    class="sticky top-0 z-10 flex items-center justify-between space-x-28 border-b bg-surface-white px-3 py-2.5 sm:px-5"
  >
    <Breadcrumbs :items="breadcrumbs" />
    <ImportSteps
      v-if="step !== 'list'"
      class="hidden flex-1 lg:flex"
      :data="data"
      :step="step"
      @updateStep="updateStep"
    />
  </header>
  <div>
    <ImportSteps
      v-if="step !== 'list'"
      class="mx-auto mt-5 flex w-[90%] flex-1 lg:hidden"
      :data="data"
      :step="step"
      @updateStep="updateStep"
    />

    <DataImportList
      v-if="step === 'list'"
      :dataImports="dataImports"
      @updateStep="updateStep"
    />

    <UploadStep
      v-else-if="step === 'upload'"
      :dataImports="dataImports"
      :doctype="doctype || data?.reference_doctype"
      :fields="fields"
      :data="data"
      @updateStep="updateStep"
    />

    <MappingStep
      v-else-if="step === 'map'"
      :dataImports="dataImports"
      :data="data"
      :fields="fields"
      @updateStep="updateStep"
    />

    <PreviewStep
      v-else-if="step === 'preview'"
      :dataImports="dataImports"
      :data="data"
      :fields="fields"
      :doctypeMap="doctypeMap"
      @updateStep="updateStep"
    />
  </div>
</template>

<script setup>
import { Breadcrumbs, createListResource, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import DataImportList from '../../../node_modules/frappe-ui/frappe/DataImport/DataImportList.vue'
import ImportSteps from '../../../node_modules/frappe-ui/frappe/DataImport/ImportSteps.vue'
import PreviewStep from '../../../node_modules/frappe-ui/frappe/DataImport/PreviewStep.vue'
import UploadStep from '@/components/DataImport/UploadStep.vue'
import MappingStep from '@/components/DataImport/MappingStep.vue'

const route = useRoute()
const step = ref('list')
const data = ref(null)

const props = defineProps({
  doctype: {
    type: String,
    default: '',
  },
  importName: {
    type: String,
    default: '',
  },
  doctypeMap: {
    type: Object,
    default: () => ({}),
  },
})

const dataImports = createListResource({
  doctype: 'Data Import',
  fields: [
    'name',
    'reference_doctype',
    'import_type',
    'status',
    'creation',
    'mute_emails',
    'import_file',
    'google_sheets_url',
    'template_options',
  ],
  auto: true,
  orderBy: 'modified desc',
})

const fields = createResource({
  url: 'frappe.desk.form.load.getdoctype',
  makeParams: (values) => ({
    doctype: values.doctype,
    with_parent: 1,
  }),
  auto: false,
})

function updateData() {
  data.value =
    dataImports.data?.find((item) => item.name === props.importName) || null
}

function loadDoctypeMeta(doctype) {
  if (!doctype) return
  fields.reload({ doctype })
}

watch(
  () => [props.doctype, props.importName, dataImports.data],
  () => {
    if (props.doctype) {
      step.value = 'upload'
      loadDoctypeMeta(props.doctype)
      return
    }

    if (!props.importName) return

    updateData()
    if (!data.value?.import_file && !data.value?.google_sheets_url) {
      step.value = 'upload'
    } else if (step.value === 'upload' && route.query.step === 'map') {
      step.value = 'map'
    } else {
      step.value = 'preview'
    }

    loadDoctypeMeta(data.value?.reference_doctype)
  },
  { immediate: true },
)

watch(
  () => route.query.step,
  (queryStep) => {
    if (queryStep === 'list') {
      step.value = 'list'
    }
    if (queryStep === 'map') {
      step.value = 'map'
    }
  },
)

function updateStep(newStep, newData) {
  step.value = newStep
  if (newData) {
    data.value = newData
    loadDoctypeMeta(newData.reference_doctype || props.doctype)
  }
}

const doctypeTitle = computed(() => {
  const activeDoctype = props.doctype || data.value?.reference_doctype || ''
  return props.doctypeMap?.[activeDoctype]?.title || activeDoctype
})

const breadcrumbs = computed(() => {
  const crumbs = [
    {
      label: 'Data Import',
      route: {
        name: 'DataImportList',
        query: { step: 'list' },
      },
    },
  ]

  if (step.value !== 'list') {
    crumbs.push({
      label: `Importing ${doctypeTitle.value}`,
    })
  }

  return crumbs
})
</script>
