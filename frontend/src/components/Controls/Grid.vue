<template>
  <div class="flex flex-col flex-1 text-base">
    <div v-if="label" class="mb-1.5 text-sm text-ink-gray-5">
      {{ __(label) }}
    </div>

    <div
      v-if="fields?.length"
      :class="isGalleryView ? 'p-4 bg-white' : ''"
    >
      <div v-if="!isGalleryView">
        <!-- Header -->
        <div
          class="grid-header flex items-center rounded-t-[7px] bg-surface-gray-2 text-ink-gray-5 truncate"
        >
        <div
          class="inline-flex items-center justify-center border-r border-outline-gray-2 h-8 p-2 w-12"
        >
          <Checkbox
            class="cursor-pointer duration-300"
            :modelValue="allRowsSelected"
            @click.stop="toggleSelectAllRows($event.target.checked)"
          />
        </div>
        <div
          class="inline-flex items-center justify-center border-r border-outline-gray-2 py-2 px-1 w-12"
        >
          {{ __('No') }}
        </div>
        <div
          class="grid w-full truncate"
          :style="{ gridTemplateColumns: gridTemplateColumns }"
        >
          <div
            v-for="field in fields"
            class="border-r border-outline-gray-2 p-2 truncate"
            :class="
              ['Int', 'Float', 'Currency', 'Percent'].includes(field.fieldtype)
                ? 'text-right'
                : ''
            "
            :key="field.fieldname"
            :title="field.label"
          >
            {{ __(field.label) }}
            <span
              v-if="
                field.reqd ||
                (field.mandatory_depends_on && field.mandatory_via_depends_on)
              "
              class="text-ink-red-2"
              >*</span
            >
          </div>
        </div>
        <div class="flex items-center justify-center w-12">
          <Button
            :tooltip="__('Edit grid fields')"
            class="rounded !bg-surface-gray-2 border-0 !text-ink-gray-5"
            variant="outline"
            icon="settings"
            @click="showGridFieldsEditorModal = true"
          />
        </div>
      </div>
      <!-- Rows -->
      <template v-if="rows?.length">
        <Draggable
          class="w-full"
          v-model="rows"
          :delay="isTouchScreenDevice() ? 200 : 0"
          group="rows"
          item-key="name"
          @end="reorder"
        >
          <template #item="{ element: row, index }">
            <div
              class="grid-row flex cursor-pointer items-center border-b border-outline-gray-modals bg-surface-modals last:rounded-b last:border-b-0"
              @click.stop="
                () => {
                  if (!gridSettings.editable_grid) {
                    showRowList[index] = true
                  }
                }
              "
            >
              <div
                class="grid-row-checkbox inline-flex h-9.5 items-center bg-surface-white justify-center border-r border-outline-gray-modals p-2 w-12"
              >
                <Checkbox
                  class="cursor-pointer duration-300"
                  :modelValue="selectedRows.has(row.name)"
                  @click.stop="toggleSelectRow(row)"
                />
              </div>
              <div
                class="flex h-9.5 items-center justify-center bg-surface-white border-r border-outline-gray-modals py-2 px-1 text-sm text-ink-gray-8 w-12"
              >
                {{ index + 1 }}
              </div>
              <div
                class="grid w-full h-9.5"
                :style="{ gridTemplateColumns: gridTemplateColumns }"
              >
                <div
                  class="border-r border-outline-gray-modals h-full"
                  v-for="field in fields"
                  :key="field.fieldname"
                >
                  <FormControl
                    v-if="
                      field.read_only &&
                      ![
                        'Int',
                        'Float',
                        'Currency',
                        'Percent',
                        'Check',
                      ].includes(field.fieldtype)
                    "
                    type="text"
                    :placeholder="field.placeholder"
                    v-model="row[field.fieldname]"
                    :disabled="true"
                  />
                  <Link
                    v-else-if="
                      ['Link', 'Dynamic Link'].includes(field.fieldtype)
                    "
                    class="text-sm text-ink-gray-8"
                    :value="row[field.fieldname]"
                    :doctype="
                      field.fieldtype == 'Link'
                        ? field.options
                        : row[field.options]
                    "
                    :filters="field.filters"
                    @change="(v) => fieldChange(v, field, row)"
                    :onCreate="
                      (value, close) => field.create(v, field, row, close)
                    "
                  />
                  <Link
                    v-else-if="field.fieldtype === 'User'"
                    class="form-control"
                    :value="getUser(row[field.fieldname]).full_name"
                    :doctype="field.options"
                    :filters="field.filters"
                    @change="(v) => fieldChange(v, field, row)"
                    :placeholder="field.placeholder"
                    :hideMe="true"
                  >
                    <template #prefix>
                      <UserAvatar
                        class="mr-2"
                        :user="row[field.fieldname]"
                        size="sm"
                      />
                    </template>
                    <template #item-prefix="{ option }">
                      <UserAvatar class="mr-2" :user="option.value" size="sm" />
                    </template>
                    <template #item-label="{ option }">
                      <Tooltip :text="option.value">
                        <div class="cursor-pointer">
                          {{ getUser(option.value).full_name }}
                        </div>
                      </Tooltip>
                    </template>
                  </Link>
                  <div
                    v-else-if="field.fieldtype === 'Check'"
                    class="flex h-full bg-surface-white justify-center items-center"
                  >
                    <Checkbox
                      class="cursor-pointer duration-300"
                      v-model="row[field.fieldname]"
                      :disabled="!gridSettings.editable_grid"
                      @change="(e) => fieldChange(e.target.checked, field, row)"
                    />
                  </div>
                  <div
                    v-else-if="field.fieldtype === 'Attach Image'"
                    class="flex h-full items-center gap-2 px-2"
                  >
                    <img
                      v-if="row[field.fieldname]"
                      :src="row[field.fieldname]"
                      class="h-7 w-7 rounded object-cover border border-outline-gray-2"
                    />
                    <ImageUploader
                      :image_url="row[field.fieldname]"
                      @upload="(url) => fieldChange(url, field, row)"
                      @remove="() => fieldChange('', field, row)"
                    />
                  </div>
                  <div
                    v-else-if="field.fieldtype === 'Attach'"
                    class="flex h-full items-center px-2"
                  >
                    <FileAttachmentInput
                      :modelValue="row[field.fieldname]"
                      :uploadLabel="__('Attach')"
                      @change="(url) => fieldChange(url, field, row)"
                    />
                  </div>
                  <TimePicker
                    v-else-if="field.fieldtype === 'Time'"
                    :value="row[field.fieldname]"
                    variant="outline"
                    :format="getFormat('', '', false, true, false)"
                    input-class="border-none text-sm text-ink-gray-8"
                    @change="(v) => fieldChange(v, field, row)"
                  />
                  <DatePicker
                    v-else-if="field.fieldtype === 'Date'"
                    :value="row[field.fieldname]"
                    variant="outline"
                    :format="getFormat('', '', true, false, false)"
                    input-class="border-none text-sm text-ink-gray-8"
                    @change="(v) => fieldChange(v, field, row)"
                  />
                  <DateTimePicker
                    v-else-if="field.fieldtype === 'Datetime'"
                    :value="row[field.fieldname]"
                    variant="outline"
                    :format="getFormat('', '', true, true, false)"
                    input-class="border-none text-sm text-ink-gray-8"
                    @change="(v) => fieldChange(v, field, row)"
                  />
                  <FormControl
                    v-else-if="
                      ['Small Text', 'Text', 'Long Text', 'Code'].includes(
                        field.fieldtype,
                      )
                    "
                    rows="1"
                    type="textarea"
                    variant="outline"
                    :value="row[field.fieldname]"
                    @change="fieldChange($event.target.value, field, row)"
                  />
                  <FormControl
                    v-else-if="field.fieldtype === 'Select'"
                    class="text-sm text-ink-gray-8"
                    type="select"
                    variant="outline"
                    v-model="row[field.fieldname]"
                    :options="field.options"
                    @change="(e) => fieldChange(e.target.value, field, row)"
                  />
                  <Password
                    v-else-if="field.fieldtype === 'Password'"
                    variant="outline"
                    :value="row[field.fieldname]"
                    :disabled="Boolean(field.read_only)"
                    @change="fieldChange($event.target.value, field, row)"
                  />
                  <FormattedInput
                    v-else-if="field.fieldtype === 'Int'"
                    class="[&_input]:text-right"
                    type="text"
                    variant="outline"
                    :value="row[field.fieldname] || '0'"
                    :disabled="Boolean(field.read_only)"
                    @change="fieldChange($event.target.value, field, row)"
                  />
                  <FormattedInput
                    v-else-if="field.fieldtype === 'Percent'"
                    class="[&_input]:text-right"
                    type="text"
                    variant="outline"
                    :value="getFloatWithPrecision(field.fieldname, row)"
                    :formattedValue="(row[field.fieldname] || '0') + '%'"
                    :disabled="Boolean(field.read_only)"
                    @change="fieldChange(flt($event.target.value), field, row)"
                  />
                  <FormattedInput
                    v-else-if="field.fieldtype === 'Float'"
                    class="[&_input]:text-right"
                    type="text"
                    variant="outline"
                    :value="getFloatWithPrecision(field.fieldname, row)"
                    :formattedValue="row[field.fieldname]"
                    :disabled="Boolean(field.read_only)"
                    @change="fieldChange(flt($event.target.value), field, row)"
                  />
                  <FormattedInput
                    v-else-if="field.fieldtype === 'Currency'"
                    class="[&_input]:text-right"
                    type="text"
                    variant="outline"
                    :value="getCurrencyWithPrecision(field.fieldname, row)"
                    :formattedValue="
                      getFormattedCurrency(field.fieldname, row, parentDoc)
                    "
                    :disabled="Boolean(field.read_only)"
                    @change="fieldChange(flt($event.target.value), field, row)"
                  />
                  <Autocomplete
                    v-else-if="field.fieldtype === 'Autocomplete'"
                    class="text-sm text-ink-gray-8"
                    :modelValue="row[field.fieldname]"
                    @update:modelValue="(v) => row[field.fieldname] = typeof v == 'object' ? v.value : v"
                    @change="(v) => fieldChange(typeof v == 'object' ? v.value : v, field, row)"
                    :options="field.options"
                    :placeholder="field.placeholder"
                    :disabled="Boolean(field.read_only)"
                  />
                  <FormControl
                    v-else
                    class="text-sm text-ink-gray-8"
                    type="text"
                    variant="outline"
                    v-model="row[field.fieldname]"
                    :options="field.options"
                    @change="fieldChange($event.target.value, field, row)"
                  />
                </div>
              </div>
              <div class="edit-row flex items-center justify-center w-12">
                <Button
                  :tooltip="__('Edit row')"
                  class="rounded border-0 !text-ink-gray-7"
                  variant="outline"
                  :icon="EditIcon"
                  @click="showRowList[index] = true"
                />
              </div>
              <GridRowModal
                v-if="showRowList[index]"
                v-model="showRowList[index]"
                v-model:showGridRowFieldsModal="showGridRowFieldsModal"
                :index="index"
                :data="row"
                :doctype="doctype"
                :parentDoctype="parentDoctype"
              />
            </div>
          </template>
        </Draggable>
      </template>
    </div>

    <template v-else>
        <div v-if="rows?.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          <div
            v-for="(row, index) in rows"
            :key="row.name"
            class="group relative aspect-square rounded-lg border border-outline-gray-modals bg-surface-gray-2 overflow-hidden flex items-center justify-center shadow-sm hover:shadow-md transition-all"
          >
            <img
              v-if="row[imageField?.fieldname]"
              :src="row[imageField.fieldname]"
              class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
            <div v-else class="text-ink-gray-3 flex flex-col items-center">
              <FeatherIcon name="image" class="h-8 w-8 mb-1" />
              <span class="text-[10px]">{{ __('No Image') }}</span>
            </div>

            <!-- Overlay Actions -->
            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <Button
                variant="solid"
                size="sm"
                icon="edit-2"
                class="!rounded-full h-8 w-8 p-0"
                @click.stop="showRowList[index] = true"
              />
              <Button
                variant="solid"
                theme="red"
                size="sm"
                icon="trash-2"
                class="!rounded-full h-8 w-8 p-0"
                @click.stop="() => {
                  selectedRows.clear();
                  selectedRows.add(row.name);
                  deleteRows();
                }"
              />
            </div>
            
            <!-- Index Badge -->
            <div class="absolute top-2 left-2 h-5 w-5 bg-white/80 backdrop-blur-sm rounded-full flex items-center justify-center text-[10px] font-bold text-ink-gray-7 shadow-sm">
              {{ index + 1 }}
            </div>

            <!-- Edit Modal -->
            <GridRowModal
              v-if="showRowList[index]"
              v-model="showRowList[index]"
              v-model:showGridRowFieldsModal="showGridRowFieldsModal"
              :index="index"
              :data="row"
              :doctype="doctype"
              :parentDoctype="parentDoctype"
            />
          </div>
        </div>
        <div v-else class="flex flex-col items-center justify-center py-12 border-2 border-dashed border-outline-gray-2 rounded-lg bg-surface-gray-1">
           <FeatherIcon name="image" class="h-10 w-10 text-ink-gray-3 mb-2" />
           <p class="text-sm text-ink-gray-5">{{ __('No images in gallery') }}</p>
        </div>
      </template>

      <div
        v-if="!isGalleryView && !rows?.length"
        class="flex flex-col items-center rounded p-5 text-sm text-ink-gray-5"
      >
        {{ __('No Data') }}
      </div>
    </div>

    <div class="mt-2 flex flex-row gap-2">
      <Button v-if="showDeleteBtn" :label="__('Delete')" variant="solid" theme="red" @click="deleteRows" />
      <Button :label="__('Add Row')" @click="addRow" />
      <Button
        v-if="imageField"
        :label="__('Bulk Upload Images')"
        @click="showBulkUploadDialog = true"
      />
      <FilesUploader
        v-if="showBulkUploadDialog"
        v-model="showBulkUploadDialog"
        :doctype="uploaderDoctype"
        :docname="uploaderDocname"
        @success="onBulkUpload"
      />
    </div>
    <GridRowFieldsModal
      v-if="showGridRowFieldsModal"
      v-model="showGridRowFieldsModal"
      :doctype="doctype"
      :parentDoctype="parentDoctype"
    />
    <GridFieldsEditorModal
      v-if="showGridFieldsEditorModal"
      v-model="showGridFieldsEditorModal"
      :doctype="doctype"
      :parentDoctype="parentDoctype"
    />
  </div>
</template>

<script setup>
import Password from '@/components/Controls/Password.vue'
import FileAttachmentInput from '@/components/Controls/FileAttachmentInput.vue'
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import FormattedInput from '@/components/Controls/FormattedInput.vue'
import GridFieldsEditorModal from '@/components/Controls/GridFieldsEditorModal.vue'
import GridRowFieldsModal from '@/components/Controls/GridRowFieldsModal.vue'
import GridRowModal from '@/components/Controls/GridRowModal.vue'
import ImageUploader from '@/components/Controls/ImageUploader.vue'
import EditIcon from '@/components/Icons/EditIcon.vue'
import Link from '@/components/Controls/Link.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { getRandom, getFormat, isTouchScreenDevice } from '@/utils'
import { flt } from '@/utils/numberFormat.js'
import { usersStore } from '@/stores/users'
import { getMeta } from '@/stores/meta'
import { createDocument } from '@/composables/document'
import {
  FormControl,
  Checkbox,
  TimePicker,
  DateTimePicker,
  DatePicker,
  Tooltip,
  dayjs,
  Autocomplete,
  FeatherIcon,
} from 'frappe-ui'
import Draggable from 'vuedraggable'
import { ref, reactive, computed, inject, provide } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: '',
  },
  doctype: {
    type: String,
    required: true,
  },
  parentDoctype: {
    type: String,
    required: true,
  },
  parentFieldname: {
    type: String,
    required: true,
  },
  overrides: {
    type: Object,
    default: () => ({}),
  }
})

const triggerOnChange = inject('triggerOnChange', () => {})
const triggerOnRowAdd = inject('triggerOnRowAdd', () => {})
const triggerOnRowRemove = inject('triggerOnRowRemove', () => {})

const {
  getGridViewSettings,
  getFields,
  getFloatWithPrecision,
  getCurrencyWithPrecision,
  getFormattedCurrency,
  getGridSettings,
} = getMeta(props.doctype)
getMeta(props.parentDoctype)
const { users, getUser } = usersStore()

const rows = defineModel()
const parentDoc = defineModel('parent')

provide('parentDoc', parentDoc)

const showRowList = ref(new Array(rows.value?.length || []).fill(false))
const selectedRows = reactive(new Set())

const showGridFieldsEditorModal = ref(false)
const showGridRowFieldsModal = ref(false)
const showBulkUploadDialog = ref(false)

const gridSettings = computed(() => getGridSettings())

const isGalleryView = computed(() => {
  return props.doctype === 'Property Image'
})

const imageField = computed(() => allFields.value.find((f) => f.fieldtype === 'Attach Image'))

const uploaderDoctype = computed(() => {
  if (!parentDoc.value?.name || parentDoc.value.name.startsWith('new-')) return null
  return props.parentDoctype
})

const uploaderDocname = computed(() => {
  const name = parentDoc.value?.name
  if (!name || name.startsWith('new-')) return null
  return name
})

function onBulkUpload(file) {
  if (!imageField.value) return
  if (!Array.isArray(rows.value)) rows.value = []

  const newRow = {}
  allFields.value?.forEach((field) => {
    if (field.fieldtype === 'Check') {
      newRow[field.fieldname] = false
    } else {
      newRow[field.fieldname] = ''
    }

    if (field.default) {
      newRow[field.fieldname] = getDefaultValue(field.default, field.fieldtype)
    }
  })

  newRow.name = getRandom(10)
  showRowList.value.push(false)
  newRow['__islocal'] = true
  newRow['idx'] = rows.value.length + 1
  newRow['doctype'] = props.doctype
  newRow['parentfield'] = props.parentFieldname
  newRow['parenttype'] = props.parentDoctype
  newRow[imageField.value.fieldname] = file.file_url

  rows.value = [...(rows.value || []), newRow]
  triggerOnRowAdd(newRow)
}

const fields = computed(() => {
  let gridViewSettings = getGridViewSettings(props.parentDoctype)
  let gridFields = getFields()
  if (gridViewSettings.length) {
    let d = gridViewSettings.map((gs) =>
      getFieldObj(gridFields.find((f) => f.fieldname === gs.fieldname)),
    )
    return d
  }
  return (
    gridFields?.filter((f) => f.in_list_view).map((f) => getFieldObj(f)) || []
  )
})

const allFields = computed(() => {
  return getFields()?.map((f) => getFieldObj(f)) || []
})

function getFieldObj(field) {
  if (field.fieldtype === 'Link' && field.options !== 'User') {
    if (!field.create) {
      field.create = (value, field, row, close) => {
        const callback = (d) => {
          if (d) fieldChange(d.name, field, row)
        }
        createDocument(field.options, value, close, callback)
      }
    }
  }

  if (field.fieldtype === 'Link' && field.options === 'User') {
    field.fieldtype = 'User'
    field.link_filters = JSON.stringify({
      ...(field.link_filters ? JSON.parse(field.link_filters) : {}),
      name: ['in', users.data.crmUsers?.map((user) => user.name)],
    })
  }

  const fieldObjWithFilters ={
    ...field,
    filters: field.link_filters && JSON.parse(field.link_filters),
    placeholder: field.placeholder || field.label,
  }
  
  return {
    ...fieldObjWithFilters,
    ...props.overrides.fields?.find(
      (f) => f.fieldname === field.fieldname,
    ),
  }
}

const gridTemplateColumns = computed(() => {
  if (!fields.value?.length) return '1fr'
  // for the checkbox & sr no. columns
  let gridViewSettings = getGridViewSettings(props.parentDoctype)
  if (gridViewSettings.length) {
    return gridViewSettings
      .map((gs) => `minmax(0, ${gs.columns || 2}fr)`)
      .join(' ')
  }
  return fields.value.map(() => `minmax(0, 2fr)`).join(' ')
})

const allRowsSelected = computed(() => {
  if (!rows.value?.length) return false
  return rows.value.length === selectedRows.size
})

const showDeleteBtn = computed(() => selectedRows.size > 0)

const toggleSelectAllRows = (iSelected) => {
  if (iSelected) {
    rows.value?.forEach((row) => selectedRows.add(row.name))
  } else {
    selectedRows.clear()
  }
}

const toggleSelectRow = (row) => {
  if (selectedRows.has(row.name)) {
    selectedRows.delete(row.name)
  } else {
    selectedRows.add(row.name)
  }
}

const addRow = () => {
  const newRow = {}
  allFields.value?.forEach((field) => {
    if (field.fieldtype === 'Check') {
      newRow[field.fieldname] = false
    } else {
      newRow[field.fieldname] = ''
    }

    if (field.default) {
      newRow[field.fieldname] = getDefaultValue(field.default, field.fieldtype)
    }
  })
  newRow.name = getRandom(10)
  showRowList.value.push(false)
  newRow['__islocal'] = true
  newRow['idx'] = rows.value.length + 1
  newRow['doctype'] = props.doctype
  newRow['parentfield'] = props.parentFieldname
  newRow['parenttype'] = props.parentDoctype
  rows.value.push(newRow)
  triggerOnRowAdd(newRow)
}

const deleteRows = () => {
  rows.value = rows.value.filter((row) => !selectedRows.has(row.name))
  triggerOnRowRemove(selectedRows, rows.value)

  showRowList.value.pop()
  selectedRows.clear()
}

const reorder = () => {
  rows.value.forEach((row, index) => {
    row.idx = index + 1
  })
}


function fieldChange(value, field, row) {
  triggerOnChange(field.fieldname, value, row)
}

function getDefaultValue(defaultValue, fieldtype) {
  if (['Float', 'Currency', 'Percent'].includes(fieldtype)) {
    return flt(defaultValue)
  } else if (fieldtype === 'Check') {
    if (['1', 'true', 'True'].includes(defaultValue)) {
      return true
    } else if (['0', 'false', 'False'].includes(defaultValue)) {
      return false
    }
  } else if (fieldtype === 'Int') {
    return parseInt(defaultValue)
  } else if (defaultValue === 'Today' && fieldtype === 'Date') {
    return dayjs().format('YYYY-MM-DD')
  } else if (
    ['Now', 'now'].includes(defaultValue) &&
    fieldtype === 'Datetime'
  ) {
    return dayjs().format('YYYY-MM-DD HH:mm:ss')
  } else if (['Now', 'now'].includes(defaultValue) && fieldtype === 'Time') {
    return dayjs().format('HH:mm:ss')
  } else if (fieldtype === 'Date') {
    return dayjs(defaultValue).format('YYYY-MM-DD')
  } else if (fieldtype === 'Datetime') {
    return dayjs(defaultValue).format('YYYY-MM-DD HH:mm:ss')
  } else if (fieldtype === 'Time') {
    return dayjs(defaultValue).format('HH:mm:ss')
  }

  return defaultValue
}
</script>

<style scoped>
/* For Input fields */
:deep(.grid-row input:not([type='checkbox'])),
:deep(.grid-row textarea) {
  border: none;
  border-radius: 0;
  height: 38px;
}

:deep(.grid-row input:focus),
:deep(.grid-row input:hover),
:deep(.grid-row textarea:focus),
:deep(.grid-row textarea:hover) {
  box-shadow: none;
}

:deep(.grid-row input:focus-within) :deep(.grid-row textarea:focus-within) {
  border: 1px solid var(--outline-gray-2);
}

/* For select field */
:deep(.grid-row select) {
  border: none;
  border-radius: 0;
  height: 38px;
}

/* For Autocomplete */
:deep(.grid-row button) {
  border: none;
  border-radius: 0;
  background-color: var(--surface-white);
  height: 38px;
}

:deep(.grid-row:last-child .grid-row-checkbox) {
  border-bottom-left-radius: 7px;
}

:deep(.grid-row .edit-row button) {
  border-bottom-right-radius: 7px;
}

:deep(.grid-row button:focus) :deep(.grid-row button:hover) {
  box-shadow: none;
  background-color: var(--surface-white);
}

:deep(.grid-row button:focus-within) {
  border: 1px solid var(--outline-gray-2);
}
</style>
