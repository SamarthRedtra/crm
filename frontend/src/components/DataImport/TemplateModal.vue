<template>
  <Dialog
    v-model="show"
    :options="{
      title: 'Export Data',
      size: '2xl',
    }"
  >
    <template #body-content>
      <div class="space-y-5 text-base">
        <div class="grid grid-cols-2 gap-5">
          <FormControl
            label="File Type"
            v-model="fileType"
            :options="['Excel', 'CSV']"
            type="select"
          />
        </div>
        <div class="border-t">
          <p class="mb-5 mt-2 text-ink-gray-5">
            Select the fields you want to include in the template.
          </p>
          <div class="mb-5 mt-2 space-x-2">
            <Button label="Select All" @click="selectAllFields" />
            <Button label="Select Mandatory Fields" @click="selectMandatoryFields" />
            <Button label="Unselect All" @click="unselectAllFields" />
          </div>
          <div v-if="fields.loading" class="py-6 text-sm text-ink-gray-5">
            Loading fields...
          </div>
          <div v-else class="space-y-8">
            <div
              v-for="doctype in Object.keys(fields.data || {})"
              :key="doctype"
              class="flex flex-col space-y-2"
            >
              <div class="text-ink-gray-5">{{ doctype }}</div>
              <div class="grid grid-cols-2 gap-5">
                <div
                  v-for="field in fields.data[doctype]"
                  :key="field.fieldname"
                  class="flex items-center space-x-2"
                >
                  <Checkbox
                    :id="`checkbox-${doctype}-${field.fieldname}`"
                    :checked="Boolean(fieldSelection[doctype]?.[field.fieldname])"
                    @change="
                      (e) => {
                        ensureDoctypeSelection(doctype)
                        fieldSelection[doctype][field.fieldname] = e.target.checked
                      }
                    "
                  />
                  <label
                    :for="`checkbox-${doctype}-${field.fieldname}`"
                    :class="{ 'text-ink-red-3': field.reqd }"
                  >
                    {{ field.label || field.fieldname }}
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <template #actions="{ close }">
      <div class="flex justify-end space-x-2">
        <Button label="Export" variant="solid" @click="handleExport" />
        <Button label="Cancel" @click="close" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { ref, watch } from 'vue'
import { fieldsToIgnore, getChildTableName } from '../../../node_modules/frappe-ui/frappe/DataImport/dataImport.ts'
import Button from '../../../node_modules/frappe-ui/src/components/Button/Button.vue'
import Checkbox from '../../../node_modules/frappe-ui/src/components/Checkbox/Checkbox.vue'
import Dialog from '../../../node_modules/frappe-ui/src/components/Dialog/Dialog.vue'
import FormControl from '../../../node_modules/frappe-ui/src/components/FormControl/FormControl.vue'

const show = defineModel({ required: true, default: false })
const fileType = ref('CSV')
const fieldSelection = ref({})
const doctypeMeta = ref(null)

const props = defineProps({
  doctype: {
    type: String,
    required: true,
  },
})

const fields = createResource({
  url: 'frappe.desk.form.load.getdoctype',
  makeParams: () => ({
    doctype: props.doctype,
    with_parent: 1,
  }),
  auto: false,
  transform(data) {
    doctypeMeta.value = data.docs || []
    return transformFields(data)
  },
})

function ensureDoctypeSelection(doctype) {
  if (!fieldSelection.value[doctype]) {
    fieldSelection.value[doctype] = {}
  }
}

function transformFields(data) {
  const doctypeMap = {}
  prepareDoctypeMap(data.docs || [], doctypeMap)
  addIDField(doctypeMap)
  updateFieldSelection(doctypeMap)
  return doctypeMap
}

function prepareDoctypeMap(docs, doctypeMap) {
  docs.forEach((doc) => {
    doctypeMap[doc.name] = (doc.fields || [])
      .filter((field) => !fieldsToIgnore.includes(field.fieldtype))
      .map((field) => ({
        fieldname: field.fieldname,
        label: field.label,
        reqd: field.reqd,
        disabled: doc.name === props.doctype && field.reqd,
      }))
  })
}

function addIDField(doctypeMap) {
  Object.keys(doctypeMap).forEach((doctype) => {
    doctypeMap[doctype].unshift({
      fieldname: 'name',
      label: 'ID',
      reqd: 1,
    })
  })
}

function updateFieldSelection(doctypeMap) {
  Object.keys(doctypeMap).forEach((doctype) => {
    ensureDoctypeSelection(doctype)

    const previousSelection = { ...fieldSelection.value[doctype] }
    fieldSelection.value[doctype] = {}

    doctypeMap[doctype].forEach((field) => {
      if (field.fieldname in previousSelection) {
        fieldSelection.value[doctype][field.fieldname] = previousSelection[field.fieldname]
      } else {
        fieldSelection.value[doctype][field.fieldname] = doctype === props.doctype && field.reqd
      }
    })
  })
}

function getExportFields() {
  const exportFields = {}
  Object.keys(fieldSelection.value).forEach((doctype) => {
    const doctypeName =
      doctype === props.doctype
        ? doctype
        : getChildTableName(doctype, props.doctype, doctypeMeta.value || [])

    exportFields[doctypeName] = Object.keys(fieldSelection.value[doctype]).filter(
      (fieldname) => fieldSelection.value[doctype][fieldname],
    )
  })
  return exportFields
}

function getExportURL() {
  const exportPageLength = ''
  return `/api/method/frappe.core.doctype.data_import.data_import.download_template
    ?doctype=${encodeURIComponent(props.doctype)}
    &export_fields=${encodeURIComponent(JSON.stringify(getExportFields()))}
    &export_records=blank_template
    &file_type=${encodeURIComponent(fileType.value)}
    &export_page_length=${exportPageLength}`.replace(/\s+/g, '')
}

async function handleExport() {
  const response = await fetch(getExportURL())
  const blob = await response.blob()
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${props.doctype}${fileType.value === 'CSV' ? '.csv' : '.xlsx'}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function selectAllFields() {
  Object.keys(fields.data || {}).forEach((doctype) => {
    ensureDoctypeSelection(doctype)
    fields.data[doctype].forEach((field) => {
      fieldSelection.value[doctype][field.fieldname] = true
    })
  })
}

function selectMandatoryFields() {
  Object.keys(fields.data || {}).forEach((doctype) => {
    ensureDoctypeSelection(doctype)
    fields.data[doctype].forEach((field) => {
      fieldSelection.value[doctype][field.fieldname] = Boolean(field.reqd)
    })
  })
}

function unselectAllFields() {
  Object.keys(fields.data || {}).forEach((doctype) => {
    ensureDoctypeSelection(doctype)
    fields.data[doctype].forEach((field) => {
      fieldSelection.value[doctype][field.fieldname] = false
    })
  })
}

watch(
  () => props.doctype,
  (doctype) => {
    if (doctype) {
      fields.reload()
    }
  },
  { immediate: true },
)

watch(
  () => show.value,
  (isOpen) => {
    if (isOpen && props.doctype) {
      fields.reload()
    }
  },
)
</script>
