<template>
  <div class="flex h-full flex-col gap-6 p-6 overflow-y-auto">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-semibold text-ink-gray-9">{{ __('Agent Settings') }}</h2>
        <p class="text-p-sm text-ink-gray-5 mt-0.5">
          {{ __('Configure KYC document requirements for agent onboarding verification.') }}
        </p>
      </div>
      <Button
        variant="solid"
        :label="__('Save')"
        :loading="saving"
        @click="saveSettings"
      />
    </div>

    <div v-if="settingsLoading" class="flex flex-1 items-center justify-center">
      <LoadingIndicator class="size-6" />
    </div>

    <div v-else class="flex flex-col gap-5">

      <!-- ── Mandatory KYC Documents ── -->
      <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-5">
        <h3 class="text-p-base font-semibold text-ink-gray-8 mb-1">
          {{ __('Mandatory KYC Document Types') }}
        </h3>
        <p class="text-p-sm text-ink-gray-5 mb-4">
          {{ __('Agents must upload all mandatory document types before submitting for verification.') }}
        </p>

        <!-- Read-only display field -->
        <div class="flex items-center gap-2 mb-3">
          <div class="flex-1">
            <label class="text-p-xs font-medium text-ink-gray-5 uppercase tracking-wide mb-1.5 block">
              {{ __('Selected Types') }}
            </label>
            <div
              class="min-h-9 w-full rounded border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-p-sm text-ink-gray-7 flex flex-wrap gap-1.5 items-center"
            >
              <template v-if="mandatoryDocs.length > 0">
                <span
                  v-for="doc in mandatoryDocs"
                  :key="doc"
                  class="inline-flex items-center gap-1 rounded bg-surface-blue-1 border border-outline-blue-1 px-2 py-0.5 text-p-xs font-medium text-blue-700"
                >
                  {{ doc }}
                  <button
                    class="ml-0.5 text-blue-400 hover:text-blue-700 leading-none"
                    @click="removeDoc(doc)"
                    :title="__('Remove')"
                  >×</button>
                </span>
              </template>
              <span v-else class="text-ink-gray-3">{{ __('None selected — all documents are optional') }}</span>
            </div>
          </div>
          <div class="self-end">
            <Button
              variant="subtle"
              iconLeft="plus"
              :label="__('Select Types')"
              @click="openSelector = true"
            />
          </div>
        </div>

        <p class="text-p-xs text-ink-gray-4">
          {{ mandatoryDocs.length > 0
              ? __(`${mandatoryDocs.length} type(s) mandatory: `) + mandatoryDocs.join(', ')
              : __('No mandatory types — agents can upload any document to verify.')
          }}
        </p>
      </div>

      <!-- ── Info Box ── -->
      <div class="flex items-start gap-3 rounded-lg bg-surface-gray-1 border border-outline-gray-2 px-4 py-3">
        <FeatherIcon name="info" class="h-4 w-4 text-ink-gray-4 shrink-0 mt-0.5" />
        <div class="text-p-sm text-ink-gray-5">
          <p class="font-medium text-ink-gray-7 mb-1">{{ __('How this works') }}</p>
          <ul class="list-disc list-inside space-y-1">
            <li>{{ __('Mandatory types appear as required checkmarks in the agent onboarding form.') }}</li>
            <li>{{ __('Agents cannot proceed to the Submit step without uploading all mandatory types.') }}</li>
            <li>{{ __('Optional types can still be uploaded but will not block submission.') }}</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ── Document Type Selector Dialog ── -->
    <Dialog
      v-model="openSelector"
      :options="{
        title: __('Select Mandatory Document Types'),
        size: 'sm',
        actions: [
          { label: __('Apply'), variant: 'solid', onClick: applySelection },
          { label: __('Cancel'), variant: 'subtle', onClick: () => openSelector = false },
        ],
      }"
    >
      <template #body-content>
        <p class="text-p-sm text-ink-gray-5 mb-4">
          {{ __('Check the document types that should be mandatory for agents.') }}
        </p>
        <div class="flex flex-col gap-1.5">
          <label
            v-for="docType in allDocTypes"
            :key="docType"
            class="flex items-center gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-colors select-none"
            :class="tempSelected.includes(docType)
              ? 'border-outline-blue-1 bg-surface-blue-1'
              : 'border-outline-gray-2 bg-surface-white hover:bg-surface-gray-1'"
          >
            <input
              type="checkbox"
              :value="docType"
              v-model="tempSelected"
              class="h-4 w-4 rounded accent-blue-600 cursor-pointer shrink-0"
            />
            <span class="text-p-sm font-medium text-ink-gray-8 flex-1">{{ docType }}</span>
            <Badge
              v-if="tempSelected.includes(docType)"
              label="Mandatory"
              variant="subtle"
              theme="blue"
              size="sm"
            />
          </label>
        </div>
        <p class="text-p-xs text-ink-gray-4 mt-3">
          {{ tempSelected.length }} of {{ allDocTypes.length }} selected
        </p>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { FeatherIcon, Button, Badge, LoadingIndicator, Dialog, createResource, toast } from 'frappe-ui'

const allDocTypes = [
  'ID Proof',
  'Address Proof',
  'License',
  'BRN Certificate',
  'Agency Agreement',
  'Photo',
  'Other',
]

const mandatoryDocs = ref([])
const tempSelected = ref([])
const openSelector = ref(false)
const saving = ref(false)
const settingsLoading = ref(true)

// Load current settings
const settingsResource = createResource({
  url: 'frappe.client.get_value',
  params: {
    doctype: 'FCRM Settings',
    fieldname: 'mandatory_kyc_documents',
    filters: { name: 'FCRM Settings' },
  },
  onSuccess(data) {
    const raw = data?.mandatory_kyc_documents || ''
    mandatoryDocs.value = raw ? raw.split(',').map(s => s.trim()).filter(Boolean) : []
    settingsLoading.value = false
  },
  onError() {
    settingsLoading.value = false
  },
})

onMounted(() => settingsResource.fetch())

// Open dialog: pre-populate with current selection
function openSelectorDialog() {
  tempSelected.value = [...mandatoryDocs.value]
  openSelector.value = true
}

// Watch when dialog opens to sync tempSelected
import { watch } from 'vue'
watch(openSelector, (val) => {
  if (val) tempSelected.value = [...mandatoryDocs.value]
})

// Apply selection — appends new types (union), doesn't remove existing
function applySelection() {
  // Merge: keep current + add newly selected; uncheck = remove
  mandatoryDocs.value = [...tempSelected.value]
  openSelector.value = false
}

// Remove a single chip
function removeDoc(doc) {
  mandatoryDocs.value = mandatoryDocs.value.filter(d => d !== doc)
}

async function saveSettings() {
  saving.value = true
  try {
    await createResource({
      url: 'frappe.client.set_value',
      makeParams() {
        return {
          doctype: 'FCRM Settings',
          name: 'FCRM Settings',
          fieldname: {
            mandatory_kyc_documents: mandatoryDocs.value.join(','),
          },
        }
      },
      onSuccess() {
        toast.success('Agent settings saved successfully')
      },
      onError(err) {
        toast.error(err.messages?.[0] || 'Failed to save settings')
      },
    }).submit()
  } finally {
    saving.value = false
  }
}
</script>
