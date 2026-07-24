<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto p-6">
    <div class="flex flex-col gap-1">
      <h2 class="text-xl font-semibold text-ink-gray-9">
        {{ __('Agent profile') }}
      </h2>
      <p class="text-p-sm text-ink-gray-5">
        {{
          __(
            'Update your agent contact details and bio. KYC documents can only be changed by your agency admin.',
          )
        }}
      </p>
    </div>

    <div
      v-if="!agentName"
      class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5 text-p-sm text-ink-gray-6"
    >
      {{ __('No agent profile is linked to your user.') }}
    </div>

    <template v-else>
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            class="w-full"
            :label="__('Phone')"
            v-model="form.phone"
            type="tel"
          />
          <FormControl
            class="w-full"
            :label="__('WhatsApp number')"
            v-model="form.whatsapp_number"
            type="tel"
          />
        </div>
        <FormControl
          class="w-full"
          :label="__('BRN/BLN ID')"
          v-model="form.brn_id"
          :description="
            __(
              'Updating your broker registration number may trigger license re-verification with DDA.',
            )
          "
        />
        <FormControl
          class="w-full"
          :label="__('About me')"
          type="textarea"
          v-model="form.bio"
        />
      </div>

      <div class="flex items-center justify-between gap-2 border-t border-outline-gray-2 pt-4">
        <ErrorMessage :message="error" />
        <Button
          variant="solid"
          :label="saving ? __('Saving…') : __('Save')"
          :loading="saving"
          :disabled="!dirty"
          @click="save"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { agentStore } from '@/stores/agent'
import { Button, FormControl, ErrorMessage, createResource, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const { agentResource } = agentStore()

const agentName = computed(() => agentResource.data?.name)

const form = ref({
  phone: '',
  whatsapp_number: '',
  bio: '',
  brn_id: '',
})

const baseline = ref(null)
const error = ref('')
const saving = ref(false)

watch(
  () => agentResource.data,
  (d) => {
    if (!d?.name) return
    const snapshot = {
      phone: d.phone || '',
      whatsapp_number: d.whatsapp_number || '',
      bio: d.bio || '',
      brn_id: d.brn_id || '',
    }
    form.value = { ...snapshot }
    baseline.value = { ...snapshot }
  },
  { immediate: true, deep: true },
)

const dirty = computed(() => {
  if (!baseline.value) return false
  return (
    form.value.phone !== baseline.value.phone ||
    form.value.whatsapp_number !== baseline.value.whatsapp_number ||
    form.value.bio !== baseline.value.bio ||
    form.value.brn_id !== baseline.value.brn_id
  )
})

const saveResource = createResource({
  url: 'crm.api.doc.update_current_agent_profile',
  makeParams() {
    return {
      phone: form.value.phone,
      whatsapp_number: form.value.whatsapp_number,
      bio: form.value.bio,
      brn_id: form.value.brn_id,
    }
  },
  onSuccess() {
    error.value = ''
    toast.success(__('Agent profile saved'))
    agentResource.reload()
  },
  onError(err) {
    error.value = err.messages?.[0] || err.message || __('Save failed')
  },
})

function save() {
  if (!agentName.value || !dirty.value) return
  saving.value = true
  saveResource.submit().finally(() => {
    saving.value = false
  })
}
</script>
