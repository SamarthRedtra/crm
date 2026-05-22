<template>
  <div class="mx-auto flex h-full w-[85%] flex-col space-y-8 pt-12 text-base lg:w-[700px]">
    <div class="flex flex-col space-y-1 text-ink-gray-7">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2 text-xl font-semibold text-ink-gray-9">
          <span>Choose Import</span>
          <Badge v-if="data?.status" :theme="getBadgeColor(data?.status)">
            {{ data?.status }}
          </Badge>
        </div>
        <Button variant="solid" @click="saveImport" :disabled="disableContinueButton">
          Continue
        </Button>
      </div>
      <div class="leading-5">
        Import data into your system using CSV files or Google Sheets.
      </div>
    </div>

    <div class="space-y-4">
      <div
        v-if="showFileSelector && !importFile"
        class="flex h-[300px] items-center justify-center rounded-md border border-dashed border-outline-gray-3 bg-surface-gray-1"
        @dragover.prevent
        @drop.prevent="(e) => uploadFile(e)"
      >
        <div v-if="showFileSelector && !uploading" class="w-4/5 text-center lg:w-2/5">
          <FeatherIcon name="upload-cloud" class="mx-auto mb-2.5 size-6 stroke-1.5 text-ink-gray-6" />
          <input
            ref="fileInput"
            type="file"
            accept=".csv"
            class="hidden"
            @change="(e) => uploadFile(e)"
          />
          <div class="leading-5 text-ink-gray-9">
            Drag and drop a CSV file, or upload from your
            <span class="cursor-pointer font-semibold hover:underline" @click="openFileSelector">
              Device
            </span>
            or
            <span class="cursor-pointer font-semibold hover:underline" @click="openSheetSelector">
              Google Sheet
            </span>
          </div>
        </div>
        <div
          v-else-if="showFileSelector && uploading"
          class="w-4/5 rounded-md border bg-surface-white p-2 lg:w-2/5"
        >
          <div class="space-y-2">
            <div class="font-medium">{{ uploadingdFile.name }}</div>
            <div class="text-ink-gray-6">
              {{ convertToKB(uploaded) }} of {{ convertToKB(total) }}
            </div>
          </div>
          <div class="mt-3 h-1 w-full rounded-full bg-surface-gray-1">
            <div
              class="h-1 rounded-full bg-surface-gray-7 transition-all duration-500 ease-in-out"
              :style="`width: ${uploadProgress}%`"
            />
          </div>
        </div>
      </div>

      <div
        v-else-if="importFile"
        class="flex h-[300px] items-center justify-center rounded-md border border-dashed border-outline-gray-3 bg-surface-gray-1"
      >
        <div class="flex w-4/5 items-center justify-between rounded-md border bg-surface-white p-2 lg:w-2/5">
          <div class="space-y-2">
            <div class="font-medium leading-5 text-ink-gray-9">
              {{ importFile.file_name || importFile.split('/').pop() }}
            </div>
            <div v-if="importFile.file_size" class="text-ink-gray-6">
              {{ convertToKB(importFile.file_size) }}
            </div>
          </div>
          <FeatherIcon
            name="trash-2"
            class="size-4 cursor-pointer stroke-1.5 text-ink-red-3"
            @click="deleteFile"
          />
        </div>
      </div>

      <div
        v-else-if="showSheetSelector"
        class="flex h-[300px] flex-col rounded-md border border-dashed border-outline-gray-3 p-4"
      >
        <div class="flex items-center space-x-2 text-ink-gray-7">
          <FeatherIcon name="chevron-left" class="size-4 cursor-pointer" @click="backToFileSelector" />
          <div>Google Sheet</div>
        </div>
        <div class="mx-auto flex w-[95%] flex-1 flex-col items-center justify-center space-y-3 lg:w-[400px]">
          <input
            v-model="googleSheet"
            type="text"
            class="w-full rounded-md border border-outline-gray-2 px-2.5 text-base"
            placeholder="Add Google Sheets Link"
          />
          <div class="text-ink-gray-5">
            Make sure the link is publically accessible to fetch the data.
          </div>
        </div>
      </div>

      <div class="flex justify-end">
        <Dropdown
          :options="[
            {
              label: 'Mandatory Fields',
              onClick() {
                exportTemplate('mandatory')
              },
            },
            {
              label: 'All Fields',
              onClick() {
                exportTemplate('all')
              },
            },
            {
              label: 'Custom Template',
              onClick() {
                showTemplateModal = true
              },
            },
          ]"
        >
          <template #default="{ open }">
            <Button variant="ghost">
              <template #prefix>
                <FeatherIcon name="download" class="size-4 stroke-1.5" />
              </template>
              Download CSV Template
              <template #suffix>
                <FeatherIcon
                  name="chevron-down"
                  :class="[
                    'ml-1 h-4 w-4 stroke-1.5 transition-transform',
                    open ? 'rotate-180' : '',
                  ]"
                />
              </template>
            </Button>
          </template>
        </Dropdown>
      </div>
    </div>

    <TemplateModal
      v-if="resolvedDoctype"
      v-model="showTemplateModal"
      :doctype="resolvedDoctype"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'frappe-ui'
import {
  fieldsToIgnore,
  getChildTableName,
  getBadgeColor,
} from '../../../node_modules/frappe-ui/frappe/DataImport/dataImport.ts'
import Badge from '../../../node_modules/frappe-ui/src/components/Badge/Badge.vue'
import Button from '../../../node_modules/frappe-ui/src/components/Button/Button.vue'
import Dropdown from '../../../node_modules/frappe-ui/src/components/Dropdown/Dropdown.vue'
import FeatherIcon from '../../../node_modules/frappe-ui/src/components/FeatherIcon.vue'
import FileUploadHandler from '../../../node_modules/frappe-ui/src/utils/fileUploadHandler'
import TemplateModal from '@/components/DataImport/TemplateModal.vue'

const emit = defineEmits(['updateStep'])

const importFile = ref(null)
const googleSheet = ref('')
const uploading = ref(false)
const uploadingdFile = ref(null)
const uploaded = ref(0)
const total = ref(0)
const showTemplateModal = ref(false)
const fileInput = ref(null)
const showFileSelector = ref(true)
const showSheetSelector = ref(false)
const showLibrarySelector = ref(false)
const router = useRouter()

const props = defineProps({
  dataImports: {
    type: Object,
    required: true,
  },
  doctype: {
    type: String,
    default: '',
  },
  fields: {
    type: Object,
    required: true,
  },
  data: {
    type: Object,
    default: null,
  },
})

const resolvedDoctype = computed(
  () => props.doctype || props.data?.reference_doctype || '',
)

const uploadProgress = computed(() => {
  if (total.value === 0) return 0
  return Math.floor((uploaded.value / total.value) * 100)
})

function extractFile(e) {
  const inputFiles = e.target?.files
  const dt = e.dataTransfer?.files
  return inputFiles?.[0] || dt?.[0] || null
}

function uploadFile(e) {
  const file = extractFile(e)
  if (!file) return

  if (file.type !== 'text/csv') {
    toast.error('Please upload a valid CSV file.')
    return
  }

  uploadingdFile.value = file
  const uploader = new FileUploadHandler()

  uploader.on('start', () => {
    uploading.value = true
  })

  uploader.on('progress', (data) => {
    uploaded.value = data.uploaded
    total.value = data.total
  })

  uploader.on('error', (error) => {
    uploading.value = false
    toast.error(error)
  })

  uploader.on('finish', () => {
    uploading.value = false
  })

  uploader
    .upload(file, {})
    .then((data) => {
      importFile.value = data
    })
    .catch((error) => {
      toast.error(error?.message || 'File upload failed.')
    })
}

function saveImport() {
  if (props.data?.name) {
    updateImport()
  } else {
    createImport()
  }
}

function createImport() {
  props.dataImports.insert.submit(
    {
      reference_doctype: resolvedDoctype.value,
      import_type: 'Insert New Records',
      mute_emails: true,
      status: 'Pending',
      google_sheets_url: googleSheet.value.trim(),
      import_file: importFile.value?.file_url,
    },
    {
      onSuccess(data) {
        router.replace({
          name: 'DataImport',
          params: { importName: data.name },
          query: { step: 'map' },
        })
      },
      onError(error) {
        toast.error(error.messages?.[0] || error)
      },
    },
  )
}

function updateImport() {
  if (!props.data) return

  props.dataImports.setValue.submit(
    {
      ...props.data,
      google_sheets_url: googleSheet.value.trim(),
      import_file: importFile.value ? importFile.value.file_url : '',
    },
    {
      onSuccess(data) {
        nextTick(() => {
          emit('updateStep', importFile.value || googleSheet.value.trim().length ? 'map' : 'upload', data)
        })
      },
      onError(error) {
        toast.error(error.messages?.[0] || error, { duration: 1000 })
      },
    },
  )
}

async function exportTemplate(type) {
  const response = await fetch(getExportURL(type))
  const blob = await response.blob()
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${resolvedDoctype.value}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function getExportURL(type) {
  return `/api/method/frappe.core.doctype.data_import.data_import.download_template
    ?doctype=${encodeURIComponent(resolvedDoctype.value)}
    &export_fields=${encodeURIComponent(JSON.stringify(getExportFields(type)))}
    &export_records=blank_template
    &file_type=CSV`.replace(/\s+/g, '')
}

function getExportFields(type) {
  return type === 'mandatory' ? getMandatoryFields() : getAllFields()
}

function getMandatoryFields() {
  const exportableFields = {}
  const docs = props.fields.data?.docs || []
  const parentDoctype = docs.find((doc) => doc.name === resolvedDoctype.value)
  if (!parentDoctype) return exportableFields

  const parentFields = (parentDoctype.fields || [])
    .filter((field) => !fieldsToIgnore.includes(field.fieldtype) && field.reqd)
    .map((field) => field.fieldname)
  parentFields.unshift('name')
  exportableFields[resolvedDoctype.value] = parentFields

  ;(parentDoctype.fields || [])
    .filter((field) => field.fieldtype === 'Table' || field.fieldtype === 'Table MultiSelect')
    .filter((field) => field.reqd)
    .forEach((field) => {
      const childDoctype = docs.find((doc) => doc.name === field.options)
      if (!childDoctype) return
      const childFields = (childDoctype.fields || [])
        .filter((f) => !fieldsToIgnore.includes(f.fieldtype) && f.reqd)
        .map((f) => f.fieldname)
      childFields.unshift('name')
      exportableFields[field.fieldname] = childFields
    })

  return exportableFields
}

function getAllFields() {
  const doctypeMap = {}
  const docs = props.fields.data?.docs || []
  docs.forEach((doc) => {
    const exportableFields = (doc.fields || [])
      .filter((field) => !fieldsToIgnore.includes(field.fieldtype))
      .map((field) => field.fieldname)
    exportableFields.unshift('name')
    const doctypeName =
      doc.name === resolvedDoctype.value
        ? doc.name
        : getChildTableName(doc.name, resolvedDoctype.value, docs)
    doctypeMap[doctypeName] = exportableFields
  })
  return doctypeMap
}

function openFileSelector() {
  fileInput.value?.click()
}

function openSheetSelector() {
  showFileSelector.value = false
  showLibrarySelector.value = false
  showSheetSelector.value = true
}

function backToFileSelector() {
  showFileSelector.value = true
  showLibrarySelector.value = false
  showSheetSelector.value = false
}

const disableContinueButton = computed(
  () => !importFile.value && !googleSheet.value.trim().length,
)

watch(
  () => props.data,
  (data) => {
    if (!data) return
    if (data.import_file) {
      importFile.value = data.import_file
      showFileSelector.value = true
      showSheetSelector.value = false
    } else if (data.google_sheets_url) {
      openSheetSelector()
      googleSheet.value = data.google_sheets_url
    }
  },
  { immediate: true },
)

watch([importFile, googleSheet], () => {
  if (props.data?.name && (!importFile.value || !googleSheet.value.trim().length)) {
    updateImport()
  }
})

function deleteFile() {
  importFile.value = null
}

function convertToKB(bytes) {
  return `${(bytes / 1024).toFixed(2)} KB`
}
</script>
