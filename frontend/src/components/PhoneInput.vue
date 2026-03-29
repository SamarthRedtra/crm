<template>
  <div class="flex w-full min-w-0 gap-2">
    <select
      :id="id ? `${id}-cc` : undefined"
      v-model="selectedDial"
      :disabled="disabled"
      :class="selectClass"
      aria-label="Country code"
    >
      <option v-for="c in PHONE_COUNTRIES" :key="c.dial" :value="c.dial">
        {{ c.label }}
      </option>
    </select>
    <input
      :id="id"
      :value="nationalDigits"
      type="tel"
      inputmode="numeric"
      autocomplete="tel-national"
      :disabled="disabled"
      :placeholder="nationalPlaceholder"
      :class="inputClassResolved"
      @input="onNationalInput"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  DEFAULT_PHONE_DIAL,
  PHONE_COUNTRIES,
  parseInternationalPhone,
  formatInternationalPhone,
} from '@/utils/phoneCountries'

const props = defineProps({
  modelValue: { type: String, default: '' },
  id: { type: String, default: undefined },
  disabled: { type: Boolean, default: false },
  /** Extra classes for the number input (select has fixed width). */
  inputClass: { type: String, default: '' },
  nationalPlaceholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

const selectedDial = ref(DEFAULT_PHONE_DIAL)
const nationalDigits = ref('')

const selectClass = computed(
  () =>
    'max-w-[min(100%,11.5rem)] shrink-0 rounded border border-outline-gray-2 bg-surface-white px-2 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100 disabled:opacity-60'
)

const inputClassResolved = computed(() => {
  const base =
    'min-w-0 flex-1 rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100 disabled:opacity-60'
  return props.inputClass ? `${base} ${props.inputClass}` : base
})

function applyFromModel(value) {
  const { dial, national } = parseInternationalPhone(value)
  selectedDial.value = PHONE_COUNTRIES.some((c) => c.dial === dial)
    ? dial
    : DEFAULT_PHONE_DIAL
  nationalDigits.value = national
}

watch(
  () => props.modelValue,
  (v) => {
    const combined = formatInternationalPhone(selectedDial.value, nationalDigits.value)
    if (v === combined) return
    applyFromModel(v)
  },
  { immediate: true }
)

watch([selectedDial, nationalDigits], () => {
  const out = formatInternationalPhone(selectedDial.value, nationalDigits.value)
  if (out !== props.modelValue) {
    emit('update:modelValue', out)
  }
})

function onNationalInput(e) {
  nationalDigits.value = e.target.value.replace(/[^\d]/g, '')
}
</script>
