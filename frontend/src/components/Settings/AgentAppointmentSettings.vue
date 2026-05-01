<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto p-6">
    <div class="flex flex-col gap-1">
      <h2 class="text-xl font-semibold text-ink-gray-9">
        {{ __('Appointment availability') }}
      </h2>
      <p class="text-p-sm text-ink-gray-5">
        {{
          __(
            'Match your Agent Onboarding “Appointment Schedule” step. You can skip scheduling during onboarding and manage it here anytime.',
          )
        }}
      </p>
    </div>

    <div v-if="!agentName" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5 text-p-sm text-ink-gray-6">
      {{ __('No agent profile is linked to your user.') }}
    </div>

    <template v-else>
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Max Daily Appointments') }}</label>
            <TextInput v-model.number="form.max_daily_appointments" type="number" size="md" />
            <p class="text-p-xs text-ink-gray-4">{{ __('Maximum appointments per day') }}</p>
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Appointment Duration (mins)') }}</label>
            <TextInput v-model.number="form.max_appointment_minutes" type="number" size="md" />
          </div>
        </div>

        <div class="overflow-hidden rounded-lg border border-outline-gray-2">
          <div
            v-for="(day, dIdx) in weekDays"
            :key="day"
            class="flex items-center gap-3 px-4 py-3 transition-colors"
            :class="[
              isDayEnabled(day) ? 'bg-surface-blue-1' : 'bg-surface-white',
              dIdx < weekDays.length - 1 ? 'border-b border-outline-gray-2' : '',
            ]"
          >
            <label class="flex w-28 shrink-0 cursor-pointer items-center gap-2.5">
              <input
                type="checkbox"
                :checked="isDayEnabled(day)"
                class="h-4 w-4 cursor-pointer rounded accent-blue-600"
                @change="toggleDay(day)"
              />
              <span
                class="text-p-sm font-medium"
                :class="isDayEnabled(day) ? 'text-blue-700' : 'text-ink-gray-6'"
              >
                {{ __(day) }}
              </span>
            </label>

            <div v-if="isDayEnabled(day)" class="flex flex-1 items-center gap-2">
              <span class="shrink-0 text-p-xs text-ink-gray-4">{{ __('From') }}</span>
              <input
                type="time"
                :value="timeInputValue(getFirstSlotForDay(day).start_time)"
                class="flex-1 rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-p-sm text-ink-gray-8 outline-none focus:border-blue-400"
                @input="(e) => setSlotTime(day, 'start_time', e.target.value)"
              />
              <span class="shrink-0 text-p-xs text-ink-gray-4">{{ __('To') }}</span>
              <input
                type="time"
                :value="timeInputValue(getFirstSlotForDay(day).end_time)"
                class="flex-1 rounded border border-outline-gray-2 bg-surface-white px-2 py-1 text-p-sm text-ink-gray-8 outline-none focus:border-blue-400"
                @input="(e) => setSlotTime(day, 'end_time', e.target.value)"
              />
            </div>
            <div v-else class="flex-1 text-p-sm text-ink-gray-3">{{ __('Not available') }}</div>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 border-t border-outline-gray-2 pt-4">
        <Button
          variant="solid"
          :label="saving ? __('Saving…') : __('Save')"
          :loading="saving"
          @click="save"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { agentStore } from '@/stores/agent'
import { Button, TextInput, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const { agentResource } = agentStore()

const weekDays = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
]

const agentName = computed(() => agentResource.data?.name)

const form = ref({
  max_daily_appointments: 10,
  max_appointment_minutes: 30,
  availability_slots: [],
})

watch(
  () => agentResource.data,
  (d) => {
    if (!d?.name) return
    form.value = {
      max_daily_appointments: d.max_daily_appointments ?? 10,
      max_appointment_minutes: d.max_appointment_minutes ?? 30,
      availability_slots: d.availability_slots ? [...d.availability_slots] : [],
    }
  },
  { immediate: true, deep: true },
)

function isDayEnabled(day) {
  return form.value.availability_slots.some((s) => s.day_of_week === day)
}

function getFirstSlotForDay(day) {
  return form.value.availability_slots.find((s) => s.day_of_week === day) || {}
}

function normalizeTimeStored(val) {
  if (!val && val !== 0) return '09:00:00'
  const s = String(val).trim()
  if (s.length === 5 && s.includes(':')) return `${s}:00`
  return s.length >= 8 ? s : `${s}:00`
}

function timeInputValue(val) {
  if (!val) return ''
  const s = String(val).trim()
  return s.length >= 5 ? s.slice(0, 5) : s
}

function setSlotTime(day, field, htmlTime) {
  const slot = form.value.availability_slots.find((s) => s.day_of_week === day)
  if (!slot) return
  slot[field] = normalizeTimeStored(htmlTime || '')
}

function toggleDay(day) {
  if (isDayEnabled(day)) {
    form.value.availability_slots = form.value.availability_slots.filter(
      (s) => s.day_of_week !== day,
    )
  } else {
    form.value.availability_slots.push({
      day_of_week: day,
      start_time: '09:00:00',
      end_time: '17:00:00',
    })
  }
}

function serializeSlotsForSave() {
  return form.value.availability_slots.map((s) => {
    const row = {
      day_of_week: s.day_of_week,
      start_time: normalizeTimeStored(s.start_time),
      end_time: normalizeTimeStored(s.end_time),
    }
    if (s.name) row.name = s.name
    return row
  })
}

const saving = ref(false)

const saveResource = createResource({
  url: 'frappe.client.set_value',
  makeParams() {
    return {
      doctype: 'Agent',
      name: agentName.value,
      fieldname: {
        max_daily_appointments: form.value.max_daily_appointments,
        max_appointment_minutes: form.value.max_appointment_minutes,
        availability_slots: serializeSlotsForSave(),
      },
    }
  },
  onSuccess() {
    toast.success(__('Appointment settings saved'))
    agentResource.reload()
  },
  onError(err) {
    toast.error(err.messages?.[0] || err.message || __('Save failed'))
  },
})

function save() {
  if (!agentName.value) return
  saving.value = true
  saveResource.submit().finally(() => {
    saving.value = false
  })
}
</script>
