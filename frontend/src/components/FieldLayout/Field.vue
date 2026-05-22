<template>
  <div v-if="field.visible" class="field">
    <div v-if="field.fieldtype != 'Check'" class="mb-2 text-sm text-ink-gray-5">
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
    <FormControl
      v-if="
        field.read_only &&
        !['Int', 'Float', 'Currency', 'Percent', 'Check'].includes(
          field.fieldtype,
        )
      "
      type="text"
      :placeholder="getPlaceholder(field)"
      v-model="data[field.fieldname]"
      :disabled="true"
      :description="field.description"
    />
    <Grid
      v-else-if="field.fieldtype === 'Table'"
      v-model="data[field.fieldname]"
      v-model:parent="data"
      :doctype="field.options"
      :parentDoctype="doctype"
      :parentFieldname="field.fieldname"
    />
    <div v-else-if="field.fieldtype === 'Attach Image'" class="space-y-2">
      <div
        v-if="data[field.fieldname]"
        class="overflow-hidden rounded border border-outline-gray-modals"
      >
        <img
          :src="data[field.fieldname]"
          :alt="field.label"
          class="h-40 w-full object-cover"
        />
      </div>
      <ImageUploader
        :image_url="data[field.fieldname]"
        :validateFile="(file) => validateIsImageFile(file, getValidationOptions(field))"
        @upload="(url) => fieldChange(url, field)"
        @remove="() => fieldChange('', field)"
      />
    </div>
    <FileAttachmentInput
      v-else-if="field.fieldtype === 'Attach'"
      :modelValue="data[field.fieldname]"
      :uploadLabel="__('Attach')"
      @change="(url) => fieldChange(url, field)"
    />
    <FormControl
      v-else-if="field.fieldtype === 'Select'"
      type="select"
      class="form-control"
      :class="field.prefix ? 'prefix' : ''"
      :options="field.options"
      v-model="data[field.fieldname]"
      @change="(e) => fieldChange(e.target.value, field)"
      :placeholder="getPlaceholder(field)"
      :description="field.description"
    >
      <template v-if="field.prefix" #prefix>
        <IndicatorIcon :class="field.prefix" />
      </template>
    </FormControl>
    <div v-else-if="field.fieldtype == 'Check'" class="flex items-center gap-2">
      <FormControl
        class="form-control"
        type="checkbox"
        v-model="data[field.fieldname]"
        @change="(e) => fieldChange(e.target.checked, field)"
        :disabled="Boolean(field.read_only)"
        :description="field.description"
      />
      <label
        class="text-sm text-ink-gray-5"
        @click="
          () => {
            if (!Boolean(field.read_only)) {
              data[field.fieldname] = !data[field.fieldname]
            }
          }
        "
      >
        {{ __(field.label) }}
        <span class="text-ink-red-3" v-if="field.mandatory">*</span>
      </label>
    </div>
    <div
      class="flex gap-1"
      v-else-if="['Link', 'Dynamic Link'].includes(field.fieldtype)"
    >
      <Link
        class="form-control flex-1 truncate"
        :value="data[field.fieldname]"
        :doctype="
          field.fieldtype == 'Link' ? field.options : data[field.options]
        "
        :filters="field.filters"
        @change="(v) => fieldChange(v, field)"
        :placeholder="getPlaceholder(field)"
        :onCreate="field.create"
      />
      <Button
        v-if="data[field.fieldname] && field.edit"
        class="shrink-0"
        :label="__('Edit')"
        :iconLeft="EditIcon"
        @click="field.edit(data[field.fieldname])"
      />
    </div>

    <TableMultiselectInput
      v-else-if="field.fieldtype === 'Table MultiSelect'"
      v-model="data[field.fieldname]"
      :doctype="field.options"
      @change="(v) => fieldChange(v, field)"
    />

    <Link
      v-else-if="field.fieldtype === 'User'"
      class="form-control"
      :value="data[field.fieldname] && getUser(data[field.fieldname]).full_name"
      :doctype="field.options"
      :filters="field.filters"
      @change="(v) => fieldChange(v, field)"
      :placeholder="getPlaceholder(field)"
      :hideMe="true"
    >
      <template #prefix>
        <UserAvatar
          v-if="data[field.fieldname]"
          class="mr-2"
          :user="data[field.fieldname]"
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
    <TimePicker
      v-else-if="field.fieldtype === 'Time'"
      :modelValue="data[field.fieldname]"
      :format="getFormat('', '', false, true, false)"
      :placeholder="getPlaceholder(field)"
      input-class="border-none"
      @update:modelValue="(v) => fieldChange(v, field)"
    />
    <input
      v-else-if="field.fieldtype === 'Datetime'"
      type="datetime-local"
      class="w-full rounded-md border border-outline-gray-3 bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none"
      :value="toDateTimeLocalValue(data[field.fieldname])"
      @input="(event) => fieldChange(fromDateTimeLocalValue(event.target.value), field)"
    />
    <DatePicker
      v-else-if="field.fieldtype === 'Date'"
      :modelValue="normalizeDateValueForPicker(data[field.fieldname])"
      :format="getFormat('', '', true, false, false)"
      :placeholder="getPlaceholder(field)"
      input-class="border-none"
      @update:modelValue="(v) => fieldChange(normalizeDateOutputFromPicker(v), field)"
    />
    <FormControl
      v-else-if="
        ['Small Text', 'Text', 'Long Text', 'Code'].includes(field.fieldtype)
      "
      type="textarea"
      :value="data[field.fieldname]"
      :placeholder="getPlaceholder(field)"
      :description="field.description"
      @change="fieldChange($event.target.value, field)"
    />
    <Password
      v-else-if="field.fieldtype === 'Password'"
      :value="data[field.fieldname]"
      :placeholder="getPlaceholder(field)"
      :description="field.description"
      @change="fieldChange($event.target.value, field)"
    />
    <FormattedInput
      v-else-if="field.fieldtype === 'Int'"
      type="text"
      :placeholder="getPlaceholder(field)"
      :value="data[field.fieldname] || '0'"
      :disabled="Boolean(field.read_only)"
      :description="field.description"
      @change="fieldChange($event.target.value, field)"
    />
    <FormattedInput
      v-else-if="field.fieldtype === 'Percent'"
      type="text"
      :value="getFormattedPercent(field.fieldname, data)"
      :placeholder="getPlaceholder(field)"
      :disabled="Boolean(field.read_only)"
      :description="field.description"
      @change="fieldChange(flt($event.target.value), field)"
    />
    <FormattedInput
      v-else-if="field.fieldtype === 'Float'"
      type="text"
      :value="getFormattedFloat(field.fieldname, data)"
      :placeholder="getPlaceholder(field)"
      :disabled="Boolean(field.read_only)"
      :description="field.description"
      @change="fieldChange(flt($event.target.value), field)"
    />
    <FormattedInput
      v-else-if="field.fieldtype === 'Currency'"
      type="text"
      :value="getFormattedCurrency(field.fieldname, data, parentDoc)"
      :placeholder="getPlaceholder(field)"
      :disabled="Boolean(field.read_only)"
      :description="field.description"
      @change="fieldChange(flt($event.target.value), field)"
    />
    <FormControl
      v-else
      type="text"
      :placeholder="getPlaceholder(field)"
      :value="getDataValue(data[field.fieldname], field)"
      :disabled="Boolean(field.read_only)"
      :description="field.description"
      @change="fieldChange($event.target.value, field)"
    />
    <div v-if="error" class="mt-1 text-xs text-red-500">
      {{ __(error) }}
    </div>
  </div>
</template>
<script setup>
import Password from '@/components/Controls/Password.vue'
import FileAttachmentInput from '@/components/Controls/FileAttachmentInput.vue'
import FormattedInput from '@/components/Controls/FormattedInput.vue'
import ImageUploader from '@/components/Controls/ImageUploader.vue'
import EditIcon from '@/components/Icons/EditIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import TableMultiselectInput from '@/components/Controls/TableMultiselectInput.vue'
import Link from '@/components/Controls/Link.vue'
import Grid from '@/components/Controls/Grid.vue'
import { createDocument } from '@/composables/document'
import {
  getFormat,
  evaluateDependsOnValue,
  normalizeDateOutputFromPicker,
  normalizeDateTimeOutputFromPicker,
  normalizeDateValueForPicker,
  normalizeDateTimeValueForPicker,
  validateIsImageFile,
} from '@/utils'
import { flt } from '@/utils/numberFormat.js'
import { getMeta } from '@/stores/meta'
import { usersStore } from '@/stores/users'
import { useDocument } from '@/data/document'
import { Tooltip, DatePicker, DateTimePicker, TimePicker, toast } from 'frappe-ui'
import { computed, provide, inject, ref, watch } from 'vue'

const props = defineProps({
  field: Object,
})

const data = inject('data')
const doctype = inject('doctype')
const preview = inject('preview')
const isGridRow = inject('isGridRow')
const fieldErrors = inject('fieldErrors', ref({}))

const error = computed(() => fieldErrors.value[field.value.fieldname])

const { getFormattedPercent, getFormattedFloat, getFormattedCurrency } =
  getMeta(doctype)

const { users, getUser } = usersStore()

let triggerOnChange
let parentDoc

if (!isGridRow) {
  const {
    triggerOnChange: trigger,
    triggerOnRowAdd,
    triggerOnRowRemove,
  } = useDocument(doctype, data.value.name)
  triggerOnChange = trigger

  provide('triggerOnChange', triggerOnChange)
  provide('triggerOnRowAdd', triggerOnRowAdd)
  provide('triggerOnRowRemove', triggerOnRowRemove)
} else {
  triggerOnChange = inject('triggerOnChange', () => {})
  parentDoc = inject('parentDoc')
}

const field = computed(() => {
  let field = props.field
  if (field.fieldtype == 'Select' && typeof field.options === 'string') {
    field.options = field.options.split('\n').map((option) => {
      return { label: option, value: option }
    })

    if (field.options[0].value !== '') {
      field.options.unshift({ label: '', value: '' })
    }
  }

  if (field.fieldtype === 'Link' && field.options === 'User') {
    field.fieldtype = 'User'
    field.link_filters = JSON.stringify({
      ...(field.link_filters ? JSON.parse(field.link_filters) : {}),
      name: ['in', users.data.crmUsers?.map((user) => user.name)],
    })
  }

  if (field.fieldtype === 'Link' && field.options !== 'User') {
    if (!field.create) {
      field.create = (value, close) => {
        const callback = (d) => {
          if (d) fieldChange(d.name, field)
        }
        createDocument(field.options, value, close, callback)
      }
    }
  }

  let _field = {
    ...field,
    filters: field.link_filters && JSON.parse(field.link_filters),
    placeholder: field.placeholder || field.label,
    display_via_depends_on: evaluateDependsOnValue(
      field.depends_on,
      data.value,
    ),
    mandatory_via_depends_on: evaluateDependsOnValue(
      field.mandatory_depends_on,
      data.value,
    ),
  }

  _field.visible = isFieldVisible(_field)
  return _field
})

function isFieldVisible(field) {
  if (preview.value) return true

  const hideEmptyReadOnly = Number(window.sysdefaults?.hide_empty_read_only_fields ?? 1)

  const shouldShowReadOnly = field.read_only && (
    data.value[field.fieldname] ||
    !hideEmptyReadOnly
  )

  return (
    (field.fieldtype == 'Check' ||
      shouldShowReadOnly ||
      !field.read_only) &&
    (!field.depends_on || field.display_via_depends_on) &&
    !field.hidden
  )
}

const getPlaceholder = (field) => {
  if (field.placeholder) {
    return __(field.placeholder)
  }
  if (['Select', 'Link'].includes(field.fieldtype)) {
    return __('Select {0}', [__(field.label)])
  } else {
    return __('Enter {0}', [__(field.label)])
  }
}

function fieldChange(value, df) {
  if (isGridRow) {
    triggerOnChange(df.fieldname, value, data.value)
  } else {
    triggerOnChange(df.fieldname, value)
  }
}

function getDataValue(value, field) {
  if (field.fieldtype === 'Duration') {
    return value || 0
  }
  return value
}

function getValidationOptions(df) {
  if (df.fieldname === 'primary_image') {
    return { exactWidth: 1024, exactHeight: 1024 }
  }
  return {}
}

function toDateTimeLocalValue(value) {
  if (!value) return ''
  return String(value).replace(' ', 'T').slice(0, 16)
}

function fromDateTimeLocalValue(value) {
  if (!value) return ''
  const normalized = String(value).replace('T', ' ')
  return normalized.length === 16 ? `${normalized}:00` : normalized
}
</script>
<style scoped>
:deep(.form-control.prefix select) {
  padding-left: 2rem;
}
</style>
