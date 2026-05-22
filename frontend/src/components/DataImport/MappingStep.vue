<template>
  <div class="mx-auto w-[85%] space-y-8 py-12 text-base lg:w-[700px]">
    <div class="flex justify-between">
      <div class="space-y-2">
        <div class="text-lg font-semibold text-ink-gray-9">
          <span>Map Data</span>
          <Badge v-if="data?.status" :theme="getBadgeColor(data?.status)">
            {{ data?.status }}
          </Badge>
        </div>
        <div class="leading-5 text-ink-gray-7">
          Change the mapping of columns from your file to fields in the system
        </div>
      </div>

      <div class="flex flex-col space-y-2 lg:flex-row lg:space-x-2 lg:space-y-0">
        <Button v-if="mappingUpdated" label="Reset Mapping" @click="resetMapping" />
        <Button label="Continue" variant="solid" @click="$emit('updateStep', 'preview')" />
      </div>
    </div>

    <div v-if="Object.keys(columnMappings).length" class="space-y-8 rounded-md border">
      <div class="grid grid-cols-2 border-b px-4 py-2 text-ink-gray-5">
        <div>Fields in File</div>
        <div>Fields in System</div>
      </div>
      <div class="grid grid-cols-2 gap-y-8 px-4 py-2">
        <template v-for="i in columnsFromFile.length" :key="i">
          <div class="text-ink-gray-7">{{ columnsFromFile[i - 1] }}</div>
          <select
            class="w-full rounded-md border border-outline-gray-3 bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none"
            :value="columnMappings[columnsFromFile[i - 1]] || ''"
            @change="(event) => updateColumnMappings(i, event.target.value)"
          >
            <option value="">Select field</option>
            <option
              v-for="option in columnsFromSystem"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Badge, Button, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import {
  fieldsToIgnore,
  getBadgeColor,
  getPreviewData,
} from '../../../node_modules/frappe-ui/frappe/DataImport/dataImport.ts'

const emit = defineEmits(['updateStep'])

const props = defineProps({
  dataImports: {
    type: Object,
    required: true,
  },
  data: {
    type: Object,
    required: true,
  },
  fields: {
    type: Object,
    required: true,
  },
})

const previewData = ref(null)
const columnMappings = ref({})
const mappingUpdated = ref(false)

function parseTemplateOptions() {
  if (!props.data?.template_options) return {}
  try {
    return JSON.parse(props.data.template_options) || {}
  } catch {
    return {}
  }
}

async function loadPreviewData() {
  if (!props.data?.name) {
    previewData.value = null
    return
  }
  previewData.value = await getPreviewData(
    props.data.name,
    props.data.import_file,
    props.data.google_sheets_url,
  )
}

const columnsFromFile = computed(() => {
  const columns = []
  previewData.value?.columns?.forEach((col) => {
    if (col.header_title !== 'Sr. No') {
      columns.push(col.header_title)
    }
  })
  return columns
})

function getChildTableName(parent, child) {
  const parentFields =
    props.fields.data?.docs?.find((doc) => doc.name === parent)?.fields || []
  const childField = parentFields.find((field) => field.options === child)
  return childField?.label || child
}

const columnsFromSystem = computed(() => {
  const parent = props.data?.reference_doctype
  const docs = props.fields.data?.docs || []

  return docs
    .map((doc) => {
      const isParent = doc.name === parent
      const columns = (doc.fields || [])
        .filter((field) => !fieldsToIgnore.includes(field.fieldtype))
        .map((field) => ({
          value: field.fieldname,
          label: isParent
            ? field.label || field.fieldname
            : `${field.label || field.fieldname} (${getChildTableName(parent, doc.name)})`,
        }))

      return [{ value: 'name', label: 'ID' }, ...columns]
    })
    .flat()
})

function findSystemValue(fieldname) {
  if (!fieldname) return ''
  return columnsFromSystem.value.some((option) => option.value === fieldname)
    ? fieldname
    : ''
}

function findAutoMappedValue(columnName) {
  return (
    columnsFromSystem.value.find((option) => option.value === columnName)?.value ||
    columnsFromSystem.value.find((option) => option.label === columnName)?.value ||
    ''
  )
}

function initializeColumnMappings() {
  if (!columnsFromFile.value.length) return

  const mappings = {}
  const templateOptions = parseTemplateOptions()
  const columnToFieldMap = templateOptions.column_to_field_map || {}
  mappingUpdated.value = Object.keys(columnToFieldMap).length > 0

  columnsFromFile.value.forEach((columnName, index) => {
    const mappedFieldname = columnToFieldMap[index]
    mappings[columnName] = mappedFieldname
      ? findSystemValue(mappedFieldname)
      : findAutoMappedValue(columnName)
  })

  columnMappings.value = mappings
}

function updateColumnMappings(index, selectedValue) {
  const columnName = columnsFromFile.value[index - 1]
  if (!columnName) return

  columnMappings.value = {
    ...columnMappings.value,
    [columnName]: selectedValue || '',
  }

  mappingUpdated.value = true
  const templateOptions = parseTemplateOptions()
  const columnToFieldMap = { ...(templateOptions.column_to_field_map || {}) }

  if (selectedValue) {
    columnToFieldMap[index - 1] = selectedValue
  } else {
    delete columnToFieldMap[index - 1]
  }

  props.dataImports.setValue.submit(
    {
      ...props.data,
      template_options: JSON.stringify({
        ...templateOptions,
        column_to_field_map: columnToFieldMap,
      }),
    },
    {
      onSuccess: (data) => {
        emit('updateStep', 'map', { ...data })
      },
      onError: (error) => {
        toast.error(error.messages?.[0] || error)
        initializeColumnMappings()
      },
    },
  )
}

function resetMapping() {
  const templateOptions = parseTemplateOptions()
  props.dataImports.setValue.submit(
    {
      ...props.data,
      template_options: JSON.stringify({
        ...templateOptions,
        column_to_field_map: {},
      }),
    },
    {
      onSuccess: (data) => {
        emit('updateStep', 'map', { ...data })
      },
      onError: (error) => {
        toast.error(error.messages?.[0] || error)
      },
    },
  )
}

watch(
  () => [props.data?.name, props.data?.import_file, props.data?.google_sheets_url],
  () => {
    loadPreviewData()
  },
  { immediate: true },
)

watch(
  () => [columnsFromFile.value, columnsFromSystem.value, props.data?.template_options],
  () => {
    initializeColumnMappings()
  },
  { immediate: true, deep: true },
)
</script>
