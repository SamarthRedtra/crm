<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">
          {{ __('Agency Profile') }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Manage your agency details, billing contacts, addons, and team access levels.') }}
        </p>
      </div>
      <Button
        variant="solid"
        :label="__('Update')"
        :loading="saveProfile.loading"
        :disabled="!isDirty"
        @click="saveProfile.submit()"
      />
    </div>

    <div v-if="management.loading" class="flex flex-1 items-center justify-center">
      <LoadingIndicator class="size-6" />
    </div>

    <div v-else-if="!management.data?.agency" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-5">
      <p class="text-p-sm text-ink-gray-6">
        {{ __('No agency is linked to your user yet.') }}
      </p>
    </div>

    <template v-else>
      <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
          <div class="mb-4">
            <h3 class="text-p-base font-semibold text-ink-gray-8">
              {{ __('Agency Details') }}
            </h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('This information is used in the agency profile and invoices.') }}
            </p>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Agency Name') }}</label>
              <input v-model="form.agency_name" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Email') }}</label>
              <input v-model="form.email" type="email" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Phone') }}</label>
              <input v-model="form.phone" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Website') }}</label>
              <input v-model="form.website" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('BRN ID') }}</label>
              <input v-model="form.brn_id" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5 md:col-span-2">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Description') }}</label>
              <textarea v-model="form.description" rows="4" :class="inputClass"></textarea>
            </div>
          </div>
        </section>

        <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
          <div class="mb-4">
            <h3 class="text-p-base font-semibold text-ink-gray-8">
              {{ __('Billing Contact') }}
            </h3>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('Billing admins can review monthly invoices and update payment setup.') }}
            </p>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Contact Name') }}</label>
              <input v-model="form.billing_contact_name" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Email') }}</label>
              <input v-model="form.billing_email" type="email" :class="inputClass" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Currency') }}</label>
              <Link
                class="form-control"
                :value="form.billing_currency"
                doctype="Currency"
                :placeholder="__('Select currency')"
                @change="(value) => (form.billing_currency = value)"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Billing Start Date') }}</label>
              <input v-model="form.billing_start_date" type="date" :class="inputClass" />
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <Badge
              :label="form.billing_status || __('Not Configured')"
              variant="subtle"
              :theme="billingStatusTheme(form.billing_status)"
            />
            <Badge
              :label="form.onboarding_status || __('Not Started')"
              variant="subtle"
              theme="blue"
            />
            <Badge
              :label="form.verification_status || __('Pending Verification')"
              variant="subtle"
              :theme="verificationStatusTheme(form.verification_status)"
            />
            <Badge
              :label="form.trial_status || __('Not Started')"
              variant="subtle"
              :theme="trialStatusTheme(form.trial_status)"
            />
          </div>
        </section>
      </div>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <div class="mb-4">
          <h3 class="text-p-base font-semibold text-ink-gray-8">
            {{ __('Address') }}
          </h3>
        </div>

        <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Address Line 1') }}</label>
            <input v-model="form.address_line1" :class="inputClass" />
          </div>
          <div class="flex flex-col gap-1.5 md:col-span-2">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Address Line 2') }}</label>
            <input v-model="form.address_line2" :class="inputClass" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('City') }}</label>
            <input v-model="form.city" :class="inputClass" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('State') }}</label>
            <input v-model="form.state" :class="inputClass" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Country') }}</label>
            <input v-model="form.country" :class="inputClass" />
          </div>
          <div class="flex flex-col gap-1.5">
            <label class="text-p-sm font-medium text-ink-gray-7">{{ __('PIN Code') }}</label>
            <input v-model="form.pincode" :class="inputClass" />
          </div>
        </div>
      </section>

      <section
        v-if="management.data.context?.can_manage_billing"
        class="rounded-lg border border-outline-gray-2 bg-surface-white p-5"
      >
        <div class="mb-4">
          <h3 class="text-p-base font-semibold text-ink-gray-8">
            {{ __('Enabled Addons') }}
          </h3>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{ __('Choose which extra services should be billed to this agency.') }}
          </p>
        </div>

        <div v-if="addonRows.length" class="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <div
            v-for="addon in addonRows"
            :key="addon.addon"
            class="rounded-lg border border-outline-gray-2 p-4"
            :class="addon.enabled ? 'bg-surface-blue-1 border-outline-blue-1' : 'bg-surface-gray-1'"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-p-base font-medium text-ink-gray-8">{{ addon.addon_name }}</p>
                <p class="mt-1 text-p-sm text-ink-gray-5">
                  {{ addon.pricing_model }} · {{ addon.catalog_rate }} {{ addon.currency }}
                </p>
                <p v-if="addon.unit_label" class="text-p-xs text-ink-gray-4">
                  {{ __('Unit: {0}', [addon.unit_label]) }}
                </p>
              </div>
              <label class="flex items-center gap-2 text-p-sm text-ink-gray-6">
                <input v-model="addon.enabled" type="checkbox" class="h-4 w-4 rounded accent-blue-600" />
                {{ __('Enabled') }}
              </label>
            </div>

            <div v-if="addon.enabled" class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div class="flex flex-col gap-1.5">
                <label class="text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Quantity') }}</label>
                <input v-model.number="addon.quantity" type="number" min="0" step="1" :class="inputClass" />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-xs font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Custom Rate') }}</label>
                <input v-model="addon.custom_rate" type="number" min="0" step="0.01" :class="inputClass" />
              </div>
            </div>
          </div>
        </div>

        <div v-else class="rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-5">
          {{ __('No billing addons have been configured yet.') }}
        </div>
      </section>

      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <div class="mb-4">
          <h3 class="text-p-base font-semibold text-ink-gray-8">
            {{ __('Team Members') }}
          </h3>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            {{ __('Admins can access billing. Managers can manage profile and team settings. Agents keep standard access.') }}
          </p>
        </div>

        <div v-if="teamMembers.length" class="flex flex-col gap-3">
          <div
            v-for="member in teamMembers"
            :key="member.name"
            class="rounded-lg border border-outline-gray-2 px-4 py-4"
          >
            <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <p class="text-p-base font-medium text-ink-gray-8">{{ member.full_name || member.user }}</p>
                  <Badge :label="member.status" variant="subtle" :theme="member.status === 'Verified' ? 'green' : 'orange'" />
                </div>
                <p class="mt-1 text-p-sm text-ink-gray-5">{{ member.email || member.user }}</p>
              </div>

              <div
                v-if="management.data.context?.can_manage_team"
                class="grid grid-cols-1 gap-3 md:grid-cols-4 xl:min-w-[720px]"
              >
                <select v-model="member.agency_role" :class="inputClass">
                  <option value="Agent">{{ __('Agent') }}</option>
                  <option value="Manager">{{ __('Manager') }}</option>
                  <option value="Admin">{{ __('Admin') }}</option>
                </select>
                <select v-model="member.agent_level" :class="inputClass">
                  <option value="">{{ __('No level') }}</option>
                  <option v-for="level in availableLevels" :key="level.name" :value="level.name">
                    {{ level.level_name }}
                  </option>
                </select>
                <label class="flex items-center gap-2 rounded border border-outline-gray-2 px-3 py-2 text-p-sm text-ink-gray-6">
                  <input v-model="member.billable" type="checkbox" class="h-4 w-4 rounded accent-blue-600" />
                  {{ __('Billable') }}
                </label>
                <Button
                  variant="subtle"
                  :label="member.saving ? __('Saving…') : __('Save Member')"
                  :disabled="member.saving"
                  @click="saveTeamMember(member)"
                />
              </div>

              <div v-else class="flex flex-wrap gap-2">
                <Badge :label="member.agency_role || __('Agent')" variant="subtle" theme="blue" />
                <Badge :label="member.agent_level || __('No level')" variant="subtle" theme="gray" />
                <Badge :label="member.billable ? __('Billable') : __('Non-billable')" variant="subtle" theme="gray" />
              </div>
            </div>
          </div>
        </div>

        <div v-else class="rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-5">
          {{ __('No agents are linked to this agency yet.') }}
        </div>
      </section>
    </template>

    <ErrorMessage :message="errorMessage || saveProfile.error" />
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { agencyStore } from '@/stores/agency'
import {
  Button,
  Badge,
  ErrorMessage,
  LoadingIndicator,
  createResource,
  call,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const { contextResource } = agencyStore()

const inputClass =
  'w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100'

const form = reactive({
  agency_name: '',
  email: '',
  phone: '',
  website: '',
  brn_id: '',
  description: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  country: '',
  pincode: '',
  billing_contact_name: '',
  billing_email: '',
  billing_currency: '',
  billing_start_date: '',
  billing_status: '',
  onboarding_status: '',
  verification_status: '',
  trial_status: '',
})

const addonRows = ref([])
const teamMembers = ref([])
const availableLevels = ref([])
const initialSnapshot = ref('')
const errorMessage = ref('')

function buildPayload() {
  return {
    ...form,
    billing_addons: addonRows.value
      .filter((row) => row.enabled)
      .map((row) => ({
        addon: row.addon,
        quantity: Number(row.quantity || 1),
        custom_rate: row.custom_rate === '' || row.custom_rate === null ? null : Number(row.custom_rate),
        enabled: 1,
      })),
  }
}

const isDirty = computed(() => {
  return initialSnapshot.value !== JSON.stringify(buildPayload())
})

function applyManagementData(data) {
  const agency = data?.agency || {}

  Object.assign(form, {
    agency_name: agency.agency_name || '',
    email: agency.email || '',
    phone: agency.phone || '',
    website: agency.website || '',
    brn_id: agency.brn_id || '',
    description: agency.description || '',
    address_line1: agency.address_line1 || '',
    address_line2: agency.address_line2 || '',
    city: agency.city || '',
    state: agency.state || '',
    country: agency.country || '',
    pincode: agency.pincode || '',
    billing_contact_name: agency.billing_contact_name || '',
    billing_email: agency.billing_email || '',
    billing_currency: agency.billing_currency || '',
    billing_start_date: agency.billing_start_date || '',
    billing_status: agency.billing_status || '',
    onboarding_status: agency.onboarding_status || '',
    verification_status: agency.verification_status || '',
    trial_status: agency.trial_status || '',
  })

  const selectedAddons = new Map(
    (agency.billing_addons || []).map((row) => [row.addon, row]),
  )
  addonRows.value = (data?.available_addons || []).map((addon) => {
    const selected = selectedAddons.get(addon.name)
    return {
      addon: addon.name,
      addon_name: addon.addon_name,
      pricing_model: addon.pricing_model,
      catalog_rate: addon.rate,
      currency: addon.currency,
      unit_label: addon.unit_label,
      enabled: Boolean(selected?.enabled),
      quantity: selected?.quantity ?? 1,
      custom_rate: selected?.custom_rate ?? '',
    }
  })

  teamMembers.value = (data?.team_members || []).map((member) => ({
    ...member,
    billable: Boolean(member.billable),
    saving: false,
  }))
  availableLevels.value = data?.available_levels || []
  initialSnapshot.value = JSON.stringify(buildPayload())
}

const management = createResource({
  url: 'crm.api.redtra.billing.get_agency_management_data',
  auto: true,
  onSuccess(data) {
    errorMessage.value = ''
    applyManagementData(data)
  },
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

const saveProfile = createResource({
  url: 'crm.api.redtra.billing.update_current_agency_profile',
  makeParams() {
    return {
      agency_id: management.data?.agency?.name,
      data: JSON.stringify(buildPayload()),
    }
  },
  onSuccess(data) {
    toast.success(__('Agency details updated successfully'))
    applyManagementData({
      ...management.data,
      agency: data.agency,
    })
    management.reload()
    contextResource.reload()
  },
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

async function saveTeamMember(member) {
  member.saving = true
  errorMessage.value = ''

  try {
    const updated = await call('crm.api.redtra.billing.update_agency_team_member', {
      agent_name: member.name,
      data: JSON.stringify({
        agency_role: member.agency_role,
        agent_level: member.agent_level || '',
        billable: member.billable ? 1 : 0,
      }),
    })

    Object.assign(member, updated, {
      billable: Boolean(updated.billable),
      saving: false,
    })
    toast.success(__('Team member updated'))
    contextResource.reload()
  } catch (error) {
    member.saving = false
    errorMessage.value = error?.messages?.[0] || error?.message
  }
}

function billingStatusTheme(status) {
  return {
    Active: 'green',
    'Past Due': 'red',
    Suspended: 'orange',
    'Not Configured': 'gray',
  }[status || 'Not Configured']
}

function verificationStatusTheme(status) {
  return {
    Verified: 'green',
    Rejected: 'red',
    'Pending Verification': 'orange',
  }[status || 'Pending Verification']
}

function trialStatusTheme(status) {
  return {
    Active: 'blue',
    Grace: 'orange',
    Expired: 'red',
    Converted: 'green',
    'Not Started': 'gray',
  }[status || 'Not Started']
}
</script>
