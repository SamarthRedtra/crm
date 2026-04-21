<template>
  <div class="flex h-full flex-col gap-6 py-8 px-6 text-ink-gray-8">
    <div class="flex justify-between px-2">
      <div class="flex w-9/12 flex-col gap-1">
        <h2 class="flex h-5 gap-2 text-xl font-semibold leading-none">
          {{ __('Invite team members') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Send email invitations to join your agency. Invited users get an Agent account and can complete agent onboarding.',
            )
          }}
        </p>
      </div>
      <div class="flex w-3/12 items-center justify-end space-x-2">
        <Button
          :label="__('Send invites')"
          variant="solid"
          :disabled="!canSubmit"
          :loading="inviteByEmail.loading"
          @click="inviteByEmail.submit()"
        />
      </div>
    </div>
    <div class="flex flex-1 flex-col gap-8 overflow-y-auto px-2">
      <div>
        <FormControl
          type="textarea"
          :label="__('Invite by email')"
          placeholder="user1@example.com, user2@example.com, ..."
          :debounce="100"
          :disabled="inviteByEmail.loading"
          :description="__('Comma-separated email addresses.')"
          @input="updateInvitees($event.target.value)"
        />
        <FormControl
          v-if="needsAgencyPicker"
          v-model="selectedAgencyId"
          type="select"
          class="mt-4"
          :label="__('Agency')"
          :options="agencySelectOptions"
          :disabled="inviteByEmail.loading || agencies.loading"
          :description="__('Select which agency these invitations apply to.')"
        />
        <FormControl
          v-model="agencyRole"
          type="select"
          class="mt-4"
          :label="__('Agency role')"
          :options="agencyRoleOptions"
        />
      </div>
    </div>
    <ErrorMessage :message="error" />
  </div>
</template>

<script setup>
import { validateEmail, convertArrayToString } from '@/utils'
import { agencyStore } from '@/stores/agency'
import { createResource, FormControl, Button, ErrorMessage } from 'frappe-ui'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'

const agency = agencyStore()
const { context } = storeToRefs(agency)

const invitees = ref([])
const agencyRole = ref('Agent')
const selectedAgencyId = ref('')
const error = ref(null)

const needsAgencyPicker = computed(
  () => Boolean(context.value?.is_internal_manager && !context.value?.agency),
)

const agencies = createResource({
  url: 'crm.api.redtra.agency_invites.list_agencies_for_team_invite',
  auto: false,
})

const agencySelectOptions = computed(() =>
  (agencies.data || []).map((a) => ({
    value: a.name,
    label: a.agency_name || a.name,
  })),
)

watch(
  needsAgencyPicker,
  (v) => {
    if (v) {
      agencies.reload()
    } else {
      selectedAgencyId.value = ''
    }
  },
  { immediate: true },
)

const canSubmit = computed(() => {
  if (!invitees.value.length) return false
  if (needsAgencyPicker.value && !selectedAgencyId.value) return false
  return true
})

const agencyRoleOptions = [
  { value: 'Agent', label: __('Agent') },
  { value: 'Manager', label: __('Manager') },
  { value: 'Admin', label: __('Admin') },
]

const inviteByEmail = createResource({
  url: 'crm.api.redtra.agency_invites.invite_agency_team_members',
  makeParams() {
    const agencyId = context.value?.agency || selectedAgencyId.value || undefined
    return {
      emails: convertArrayToString(invitees.value),
      agency_role: agencyRole.value,
      agency_id: agencyId,
    }
  },
  onSuccess() {
    invitees.value = []
    error.value = null
  },
  onError(err) {
    error.value = err?.messages?.[0] || err?.message
  },
})

function updateInvitees(value) {
  const emails = value
    .split(',')
    .map((email) => email.trim())
    .filter((email) => validateEmail(email))
  invitees.value = emails
}
</script>
