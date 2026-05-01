<template>
  <div class="space-y-1.5 p-[2px] -m-[2px]">
    <label class="block" :class="labelClasses" v-if="attrs.label">
      {{ __(attrs.label) }}
    </label>
    <Autocomplete
      ref="autocomplete"
      :options="options.data || []"
      v-model="value"
      :size="attrs.size || 'sm'"
      :variant="attrs.variant"
      :placeholder="attrs.placeholder"
      :disabled="attrs.disabled"
      :placement="attrs.placement"
      :filterable="false"
      @update:query="onQueryChange"
    >
      <template #target="{ open, togglePopover }">
        <slot v-if="$slots.target" name="target" v-bind="{ open, togglePopover }" />
        <button
          v-else
          type="button"
          class="relative flex h-7 w-full items-center justify-between gap-2 rounded px-2 py-1 transition-colors bg-surface-gray-2 border border-surface-gray-3 text-ink-gray-8"
          :disabled="attrs.disabled"
          @click="() => !attrs.disabled && togglePopover()"
        >
          <div v-if="value" class="flex text-base leading-5 items-center truncate">
            <span class="truncate">{{ value }}</span>
          </div>
          <div v-else class="absolute text-ink-gray-4 text-left truncate w-full pr-7">
            {{ attrs.placeholder || '' }}
          </div>
          <FeatherIcon
            v-if="!attrs.disabled"
            name="chevron-down"
            class="absolute h-4 w-4 text-ink-gray-5 right-2"
            aria-hidden="true"
          />
        </button>
      </template>

      <template #prefix v-if="$slots.prefix">
        <slot name="prefix" />
      </template>

      <template #item-prefix="{ active, selected, option }" v-if="$slots['item-prefix']">
        <slot name="item-prefix" v-bind="{ active, selected, option }" />
      </template>

      <template #item-label="{ active, selected, option }">
        <slot name="item-label" v-bind="{ active, selected, option }">
          <div v-if="option?.description" class="flex flex-col gap-1">
            <div class="flex-1 font-semibold truncate text-ink-gray-7">
              {{ option?.label }}
            </div>
            <div class="flex-1 text-sm truncate text-ink-gray-5">
              {{ option?.description }}
            </div>
          </div>
          <div v-else class="flex-1 truncate text-ink-gray-7">
            {{ option?.label }}
          </div>
        </slot>
      </template>

      <template #footer="{ value, close }">
        <div v-if="attrs.onCreate">
          <Button
            variant="ghost"
            class="w-full !justify-start"
            :label="__('Create New')"
            iconLeft="plus"
            @click="() => attrs.onCreate(value, close)"
          />
        </div>
        <div>
          <Button
            variant="ghost"
            class="w-full !justify-start"
            :label="__('Clear')"
            iconLeft="x"
            @click="() => clearValue(close)"
          />
        </div>
      </template>
    </Autocomplete>
  </div>
</template>

<script setup>
import Autocomplete from '@/components/frappe-ui/Autocomplete.vue'
import { watchDebounced } from '@vueuse/core'
import { createResource } from 'frappe-ui'
import { useAttrs, computed, ref } from 'vue'

const props = defineProps({
  doctype: {
    type: String,
    required: true,
  },
  filters: {
    type: [Array, Object, String],
    default: [],
  },
  modelValue: {
    type: String,
    default: '',
  },
  hideMe: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const attrs = useAttrs()

const valuePropPassed = computed(() => 'value' in attrs)

const value = computed({
  get: () => (valuePropPassed.value ? attrs.value : props.modelValue),
  set: (val) => {
    const newValue = val && typeof val === 'object' && 'value' in val ? val.value : val
    emit(valuePropPassed.value ? 'change' : 'update:modelValue', newValue)
  },
})

const autocomplete = ref(null)
const text = ref('')

watchDebounced(
  text,
  (val) => {
    reload(val)
  },
  { debounce: 300 }
)

function onQueryChange(val) {
  val = val || ''
  if (text.value === val) return
  text.value = val
}

watchDebounced(
  () => props.doctype,
  () => reload(''),
  { debounce: 300, immediate: true },
)

watchDebounced(
  () => props.filters,
  () => {
    reload('', true)
  },
  { debounce: 300, immediate: true },
)

const options = createResource({
  url: 'frappe.desk.search.search_link',
  cache: [props.doctype, text.value, props.hideMe, JSON.stringify(props.filters)],
  method: 'POST',
  params: {
    txt: text.value,
    doctype: props.doctype,
    filters: props.filters,
  },
  transform: (data) => {
    console.log('[Link.vue] transform data:', data)
    if (data && data.message && Array.isArray(data.message)) {
      data = data.message
    }
    if (!data || !Array.isArray(data)) return []
    let allData = data.map((option) => {
      return {
        label: option?.label || option?.value || '',
        value: option?.value || '',
        description: option?.description || '',
      }
    })
    if (!props.hideMe && props.doctype == 'User') {
      allData.unshift({
        label: '@me',
        value: '@me',
      })
    }
    return allData
  },
})

function reload(val, force=false) {
  if (!props.doctype) return
  if (
    !force &&
    options.data?.length &&
    val === options.params?.txt &&
    props.doctype === options.params?.doctype
  ) 
    return

  options.update({
    params: {
      txt: val,
      doctype: props.doctype,
      filters: props.filters,
    },
  })
  options.reload()
}

function clearValue(close) {
  emit(valuePropPassed.value ? 'change' : 'update:modelValue', '')
  close()
}

const labelClasses = computed(() => {
  return [
    {
      sm: 'text-xs',
      md: 'text-base',
    }[attrs.size || 'sm'],
    'text-ink-gray-5',
  ]
})
</script>
