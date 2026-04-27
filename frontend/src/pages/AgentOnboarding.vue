<template>
  <div class="flex h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-2xl rounded-xl bg-surface-white shadow-sm border border-outline-gray-2 flex flex-col max-h-[92vh] overflow-y-auto">

      <!-- ── Header ── -->
      <div class="flex flex-col items-center gap-2 px-8 pt-8 pb-5 border-b border-outline-gray-2">
        <div class="flex items-center justify-center h-11 w-11 rounded-lg bg-surface-blue-1">
          <FeatherIcon name="shield" class="h-5 w-5 text-blue-600" />
        </div>
        <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Agent Onboarding') }}</h1>
        <p class="text-p-sm text-ink-gray-5 text-center">
          {{ __('Complete all sections to submit your profile for verification.') }}
        </p>
        <Button
          v-if="showAgencyOnboardingLink"
          variant="subtle"
          class="mt-1"
          :label="__('Agency profile & billing')"
          iconLeft="building"
          @click="goAgencyOnboarding"
        />
      </div>

      <!-- ── Agency Status Banner ── -->
      <div v-if="agencyStatus === 'Pending Verification' || agencyStatus === 'Rejected'" class="px-8 py-3 bg-surface-yellow-1 border-b border-outline-yellow-1 flex items-center gap-3 dark:bg-amber-900/10 dark:border-amber-800/50">
        <FeatherIcon :name="agencyStatus === 'Rejected' ? 'alert-circle' : 'info'" class="h-4 w-4" :class="agencyStatus === 'Rejected' ? 'text-red-600 dark:text-red-500' : 'text-yellow-600 dark:text-amber-500'" />
        <p class="text-p-xs flex-1" :class="agencyStatus === 'Rejected' ? 'text-red-800 dark:text-red-200' : 'text-yellow-800 dark:text-amber-100'">
          <span class="font-semibold">{{ agencyStatus === 'Rejected' ? __('Agency Verification Rejected:') : __('Agency Verification Pending:') }}</span>
          {{ agencyStatus === 'Rejected' 
              ? __('Your agency profile was rejected. Please contact the administrator or check your agency profile.') 
              : __('The agency profile is currently under review. You can proceed with your onboarding, but full CRM access requires agency verification.') 
          }}
        </p>
        <Button v-if="agencyContext?.can_manage_billing" variant="subtle" size="sm" :label="__('Fix Agency Profile')" @click="goAgencyOnboarding" />
      </div>

      <div class="px-8 py-6 flex flex-col gap-6">

        <!-- ════════════════════════════
             VERIFIED STATE
        ════════════════════════════ -->
        <div v-if="localStatus === 'Verified'" class="flex flex-col items-center gap-4 py-4">
          <div class="flex items-center justify-center h-16 w-16 rounded-full bg-surface-green-1">
            <FeatherIcon name="check-circle" class="h-8 w-8 text-green-600" />
          </div>
          <div class="text-center">
            <h2 class="text-xl font-semibold text-ink-gray-9 mb-1">{{ __('Account Verified') }}</h2>
            <p class="text-p-sm text-ink-gray-5">{{ __('Your agent account is verified. You now have full access to the CRM platform.') }}</p>
          </div>
          <div class="flex flex-wrap gap-2 justify-center">
            <Badge label="Leads & Deals" variant="subtle" theme="blue" />
            <Badge label="Properties" variant="subtle" theme="blue" />
            <Badge label="Contacts" variant="subtle" theme="blue" />
            <Badge label="Calendar & Tasks" variant="subtle" theme="blue" />
          </div>
          <Button variant="solid" :label="__('Go to CRM Dashboard')" iconRight="arrow-right" @click="goToCRM" />

          <!-- Read-only profile summary -->
          <div class="w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-4 mt-2">
            <p class="text-p-sm font-semibold text-ink-gray-7 mb-3">{{ __('Your Submitted Profile') }}</p>
            <div class="grid grid-cols-2 gap-3 text-p-sm">
              <div><span class="text-ink-gray-4">DLD ID:</span> <span class="font-medium text-ink-gray-8">{{ formData.dfd_registration_id }}</span></div>
              <div><span class="text-ink-gray-4">BRN/BLN ID:</span> <span class="font-medium text-ink-gray-8">{{ formData.brn_id || '—' }}</span></div>
              <div><span class="text-ink-gray-4">Phone:</span> <span class="font-medium text-ink-gray-8">{{ formData.phone || '—' }}</span></div>
              <div><span class="text-ink-gray-4">WhatsApp:</span> <span class="font-medium text-ink-gray-8">{{ formData.whatsapp_number || '—' }}</span></div>
            </div>
            <div v-if="formData.kyc_documents.length > 0" class="mt-3 pt-3 border-t border-outline-gray-2">
              <p class="text-p-xs text-ink-gray-4 mb-2">KYC Documents ({{ formData.kyc_documents.length }})</p>
              <div class="flex flex-col gap-1.5">
                <div v-for="doc in formData.kyc_documents" :key="doc.name" class="flex items-center gap-2 text-p-sm">
                  <FeatherIcon name="file" class="h-3.5 w-3.5 text-ink-gray-4 shrink-0" />
                  <span class="text-ink-gray-7 flex-1 truncate">{{ getFileName(doc.document_file) }}</span>
                  <Badge :label="doc.document_type" variant="subtle" theme="blue" size="sm" />
                  <Badge :label="doc.doc_status || 'Pending'" variant="subtle" :theme="statusTheme(doc.doc_status)" size="sm" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ════════════════════════════
             PENDING STATE
        ════════════════════════════ -->
        <div v-else-if="localStatus === 'Pending Verification'" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-6">
          <div class="flex gap-3 items-start">
            <div class="flex items-center justify-center h-8 w-8 rounded-md bg-surface-yellow-1 shrink-0 mt-0.5">
              <FeatherIcon name="clock" class="h-4 w-4 text-yellow-600" />
            </div>
            <div>
              <p class="text-p-base font-medium text-ink-gray-9">{{ __('Verification Under Review') }}</p>
              <p class="text-p-sm text-ink-gray-5 mt-0.5">{{ __('Your profile has been submitted and is under review by our team.') }}</p>
            </div>
          </div>

          <!-- Doc-level status -->
          <div v-if="formData.kyc_documents.length" class="mt-4 flex flex-col gap-1.5">
            <p class="text-p-xs font-medium text-ink-gray-5 mb-1">{{ __('Document Review Status') }}</p>
            <div
              v-for="doc in formData.kyc_documents"
              :key="doc.name"
              class="flex items-center gap-3 rounded-md border px-3 py-2 text-p-sm"
              :class="{
                'border-outline-green-1 bg-surface-green-1': doc.doc_status === 'Approved',
                'border-outline-red-1 bg-surface-red-1': doc.doc_status === 'Rejected',
                'border-outline-gray-2 bg-surface-white': !doc.doc_status || doc.doc_status === 'Pending',
              }"
            >
              <FeatherIcon
                :name="doc.doc_status === 'Approved' ? 'check-circle' : doc.doc_status === 'Rejected' ? 'x-circle' : 'clock'"
                class="h-4 w-4 shrink-0"
                :class="{
                  'text-green-500': doc.doc_status === 'Approved',
                  'text-red-500': doc.doc_status === 'Rejected',
                  'text-ink-gray-3': !doc.doc_status || doc.doc_status === 'Pending',
                }"
              />
              <span class="flex-1 font-medium text-ink-gray-7">{{ doc.document_type }}</span>
              <span class="text-ink-gray-4 truncate text-p-xs">{{ getFileName(doc.document_file) }}</span>
            </div>
          </div>
        </div>

        <!-- ════════════════════════════
             FORM STATE (Draft / Rejected)
        ════════════════════════════ -->
        <template v-else>

          <!-- Rejected alert -->
          <div v-if="localStatus === 'Rejected'" class="flex items-start gap-3 rounded-lg bg-surface-red-1 border border-outline-red-1 px-4 py-3">
            <FeatherIcon name="x-circle" class="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
            <p class="text-p-sm text-red-700">
              <span class="font-semibold">{{ __('Verification Rejected.') }}</span>
              {{ __(' Some documents were rejected. Please review the comments below and re-upload.') }}
            </p>
          </div>

          <!-- ── Progress ── -->
          <div class="flex flex-col gap-2">
            <div class="flex items-center">
              <div v-for="(sec, idx) in sections" :key="idx" class="flex items-center flex-1">
                <button
                  class="flex items-center gap-2 shrink-0"
                  @click="tryGoToStep(idx)"
                >
                  <div
                    class="flex items-center justify-center h-6 w-6 rounded-full text-p-xs font-semibold shrink-0 transition-colors"
                    :class="{
                      'bg-blue-600 text-white': activeSection === idx,
                      'bg-surface-green-1 text-green-600': activeSection > idx,
                      'bg-surface-gray-2 text-ink-gray-4': activeSection < idx,
                    }"
                  >
                    <FeatherIcon v-if="activeSection > idx" name="check" class="h-3.5 w-3.5" />
                    <span v-else>{{ idx + 1 }}</span>
                  </div>
                  <span class="text-p-sm font-medium hidden sm:block" :class="{
                    'text-blue-600': activeSection === idx,
                    'text-green-600': activeSection > idx,
                    'text-ink-gray-4': activeSection < idx,
                  }">{{ sec.label }}</span>
                </button>
                <div v-if="idx < sections.length - 1" class="flex-1 mx-2 h-px" :class="activeSection > idx ? 'bg-green-400' : 'bg-outline-gray-2'"></div>
              </div>
            </div>
            <div class="h-1 w-full rounded-full bg-surface-gray-2">
              <div class="h-1 rounded-full bg-blue-600 transition-all duration-300" :style="{ width: (activeSection / (sections.length - 1)) * 100 + '%' }"></div>
            </div>
            <p class="text-p-xs text-ink-gray-4 text-right">
              {{ __('Step {0} of {1}: {2}', [activeSection + 1, sections.length, sections[activeSection].label]) }}
            </p>
          </div>

          <!-- ════ STEP 1: BASIC INFO ════ -->
          <div v-show="activeSection === 0" class="flex flex-col gap-4">
            <div class="flex items-center gap-2 mb-1">
              <FeatherIcon name="user" class="h-4 w-4 text-ink-gray-5" />
              <h3 class="text-p-base font-semibold text-ink-gray-8">{{ __('Basic Information') }}</h3>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('DLD Registration ID') }} <span class="text-red-500">*</span></label>
                <TextInput v-model="formData.dfd_registration_id" :placeholder="__('e.g. 12345')" size="md" />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('BRN/BLN ID') }}</label>
                <TextInput v-model="formData.brn_id" :placeholder="__('e.g. 67890')" size="md" />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Phone') }}</label>
                <PhoneInput v-model="formData.phone" :national-placeholder="__('50 000 0000')" />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('WhatsApp Number') }}</label>
                <PhoneInput v-model="formData.whatsapp_number" :national-placeholder="__('50 000 0000')" />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Zone Name') }}</label>
                <TextInput v-model="formData.zone_name" placeholder="e.g. Downtown Dubai" size="md" />
              </div>
            </div>
            
            <div class="flex flex-col gap-1.5">
              <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Bio') }}</label>
              <textarea
                v-model="formData.bio"
                rows="3"
                class="w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 placeholder:text-ink-gray-3 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 resize-none transition"
                :placeholder="__('Tell us about yourself, experience and specialties…')"
              ></textarea>
            </div>
          </div>

          <!-- ════ STEP 2: DOCUMENTS ════ -->
          <div v-show="activeSection === 1" class="flex flex-col gap-4">
            <div class="flex items-center gap-2 mb-1">
              <FeatherIcon name="file-text" class="h-4 w-4 text-ink-gray-5" />
              <h3 class="text-p-base font-semibold text-ink-gray-8">{{ __('Upload Documents') }}</h3>
            </div>
            <p class="text-p-sm text-ink-gray-5 -mt-2">{{ __('Upload required verification documents. Accepted: PDF, JPG, PNG (max 10 MB).') }}</p>

            <!-- Mandatory doc types checklist -->
            <div v-if="mandatoryDocTypes.length > 0" class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div
                v-for="dt in mandatoryDocTypes"
                :key="dt"
                class="flex items-center gap-2.5 rounded-md border px-3 py-2 text-p-sm transition-colors"
                :class="hasDocType(dt) ? 'border-outline-green-1 bg-surface-green-1' : 'border-outline-gray-2 bg-surface-gray-1'"
              >
                <FeatherIcon :name="hasDocType(dt) ? 'check-circle' : 'circle'" class="h-4 w-4 shrink-0" :class="hasDocType(dt) ? 'text-green-500' : 'text-ink-gray-3'" />
                <span class="flex-1 font-medium text-ink-gray-8">{{ dt }}</span>
                <Badge v-if="hasDocType(dt)" label="✓ Uploaded" variant="subtle" theme="green" size="sm" />
                <Badge v-else label="Required" variant="subtle" theme="red" size="sm" />
              </div>
            </div>

            <!-- Rejected documents that need re-upload -->
            <div v-if="rejectedDocs.length > 0" class="rounded-lg border border-outline-red-1 bg-surface-red-1 p-4">
              <div class="flex items-center gap-2 mb-3">
                <FeatherIcon name="alert-triangle" class="h-4 w-4 text-red-600 shrink-0" />
                <p class="text-p-sm font-semibold text-red-700">{{ __('Documents Requiring Re-upload') }}</p>
              </div>
              <div class="flex flex-col gap-2">
                <div v-for="(doc, idx) in rejectedDocs" :key="idx" class="bg-white rounded-md border border-outline-red-1 p-3">
                  <div class="flex items-center justify-between gap-2 mb-1.5">
                    <div class="flex items-center gap-2">
                      <FeatherIcon name="file" class="h-3.5 w-3.5 text-red-400 shrink-0" />
                      <span class="text-p-sm font-medium text-ink-gray-8">{{ doc.document_type }}</span>
                    </div>
                    <Badge label="Rejected" variant="subtle" theme="red" size="sm" />
                  </div>
                  <p v-if="doc.admin_comment" class="text-p-xs text-red-600 mb-2">
                    <span class="font-semibold">{{ __('Admin comment:') }}</span> {{ doc.admin_comment }}
                  </p>
                  <Button variant="subtle" size="sm" iconLeft="upload" :label="__('Re-upload')" @click="triggerRejectedReupload(doc)" />
                </div>
              </div>
            </div>

            <!-- Upload area (hidden for non-rejected docs if status is Rejected) -->
            <FileUploader @success="(file) => handleDocumentUpload(file)" :validateFile="validateIsDocument" :multiple="true">
              <template #default="{ openFileSelector, uploading, progress }">
                <div
                  class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-outline-gray-3 p-8 transition-colors hover:bg-surface-gray-1 hover:border-blue-400"
                  @click="openFileSelector"
                  :id="'kyc-uploader-trigger'"
                >
                  <FeatherIcon :name="uploading ? 'loader' : 'upload-cloud'" class="h-7 w-7 text-ink-gray-4" :class="{ 'animate-spin': uploading }" />
                  <p class="text-p-sm font-medium text-ink-gray-6">
                    {{ uploading ? __('Uploading… {0}%', [progress]) : __('Click or drag files here to upload') }}
                  </p>
                  <p class="text-p-xs text-ink-gray-4">{{ __('PDF, JPG, PNG — max 10 MB') }}</p>
                </div>
              </template>
            </FileUploader>

            <!-- Uploaded list -->
            <div v-if="formData.kyc_documents.length > 0" class="flex flex-col gap-1">
              <p class="text-p-xs font-medium text-ink-gray-5 mb-1">{{ __('Uploaded ({0})', [formData.kyc_documents.length]) }}</p>
              <div v-for="(doc, idx) in formData.kyc_documents" :key="idx" class="flex items-center gap-3 rounded-md border border-outline-gray-2 bg-surface-gray-1 px-3 py-2">
                <FeatherIcon name="file" class="h-4 w-4 text-ink-gray-4 shrink-0" />
                <div class="flex-1 min-w-0 flex flex-col sm:flex-row sm:items-center gap-2">
                  <span class="text-p-sm font-medium text-ink-gray-8 truncate flex-1">{{ getFileName(doc.document_file) }}</span>
                  <select v-model="doc.document_type" class="text-p-sm border border-outline-gray-2 rounded bg-surface-white text-ink-gray-8 px-2 py-1 outline-none focus:border-blue-400 cursor-pointer sm:w-56">
                    <option value="" disabled>{{ __('Select type…') }}</option>
                    <option value="ID Proof">{{ __('ID Proof (Emirates ID / Passport)') }}</option>
                    <option value="Address Proof">{{ __('Address Proof (Utility Bill)') }}</option>
                    <option value="License">{{ __('Real Estate License (RERA/DLD)') }}</option>
                    <option value="BRN Certificate">{{ __('BRN Certificate') }}</option>
                    <option value="Agency Agreement">{{ __('Agency Agreement') }}</option>
                    <option value="Photo">{{ __('Passport-size Photo') }}</option>
                    <option value="Other">{{ __('Other') }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <Badge v-if="doc.doc_status === 'Approved'" label="Approved" variant="subtle" theme="green" size="sm" />
                  <Badge v-else-if="doc.doc_status === 'Rejected'" label="Rejected" variant="subtle" theme="red" size="sm" />
                  <Button variant="ghost" size="sm" icon="trash-2" class="text-red-500" @click="removeDoc(idx)" />
                </div>
              </div>
            </div>
          </div>

          <!-- ════ STEP 3: APPOINTMENT SCHEDULE ════ -->
          <div v-show="activeSection === 2" class="flex flex-col gap-4">
            <div class="flex items-center gap-2 mb-1">
              <FeatherIcon name="calendar" class="h-4 w-4 text-ink-gray-5" />
              <h3 class="text-p-base font-semibold text-ink-gray-8">{{ __('Appointment Schedule') }}</h3>
            </div>
            <p class="text-p-sm text-ink-gray-5 -mt-2">{{ __('Set your weekly availability so clients can schedule property viewings.') }}</p>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Max Daily Appointments') }}</label>
                <TextInput type="number" v-model="formData.max_daily_appointments" size="md" />
                <p class="text-p-xs text-ink-gray-4">{{ __('Maximum appointments per day') }}</p>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Appointment Duration (mins)') }}</label>
                <TextInput type="number" v-model="formData.max_appointment_minutes" size="md" />
              </div>
            </div>

            <!-- Weekly schedule — checkbox enables the day; single From/To per day -->
            <div class="rounded-lg border border-outline-gray-2 overflow-hidden">
              <div
                v-for="(day, dIdx) in weekDays" :key="day"
                class="flex items-center gap-3 px-4 py-3 transition-colors"
                :class="[
                  isDayEnabled(day) ? 'bg-surface-blue-1' : 'bg-surface-white',
                  dIdx < weekDays.length - 1 ? 'border-b border-outline-gray-2' : ''
                ]"
              >
                <label class="flex items-center gap-2.5 cursor-pointer w-28 shrink-0">
                  <input type="checkbox" :checked="isDayEnabled(day)" @change="toggleDay(day)" class="h-4 w-4 rounded accent-blue-600 cursor-pointer" />
                  <span class="text-p-sm font-medium" :class="isDayEnabled(day) ? 'text-blue-700' : 'text-ink-gray-6'">{{ day }}</span>
                </label>

                <div v-if="isDayEnabled(day)" class="flex items-center gap-2 flex-1">
                  <span class="text-p-xs text-ink-gray-4 shrink-0">From</span>
                  <input type="time" v-model="getFirstSlotForDay(day).start_time" class="flex-1 rounded border border-outline-gray-2 px-2 py-1 text-p-sm text-ink-gray-8 bg-surface-white outline-none focus:border-blue-400" />
                  <span class="text-p-xs text-ink-gray-4 shrink-0">To</span>
                  <input type="time" v-model="getFirstSlotForDay(day).end_time" class="flex-1 rounded border border-outline-gray-2 px-2 py-1 text-p-sm text-ink-gray-8 bg-surface-white outline-none focus:border-blue-400" />
                </div>
                <div v-else class="flex-1 text-p-sm text-ink-gray-3">{{ __('Not available') }}</div>
              </div>
            </div>
          </div>

          <!-- ════ STEP 4: REVIEW & SUBMIT ════ -->
          <div v-show="activeSection === 3" class="flex flex-col gap-4">
            <div class="flex items-center gap-2 mb-1">
              <FeatherIcon name="check-square" class="h-4 w-4 text-ink-gray-5" />
              <h3 class="text-p-base font-semibold text-ink-gray-8">{{ __('Review & Submit') }}</h3>
            </div>

            <div class="rounded-lg border border-outline-gray-2 overflow-hidden">
              <div v-for="(item, idx) in reviewItems" :key="idx"
                class="flex items-center gap-3 px-4 py-3"
                :class="[item.ok ? 'bg-surface-white' : 'bg-surface-red-1', idx < reviewItems.length - 1 ? 'border-b border-outline-gray-2' : '']"
              >
                <FeatherIcon :name="item.ok ? 'check-circle' : 'alert-circle'" class="h-4 w-4 shrink-0" :class="item.ok ? 'text-green-500' : 'text-red-500'" />
                <span class="text-p-sm font-medium text-ink-gray-7 flex-1">{{ item.label }}</span>
                <span class="text-p-sm" :class="item.ok ? 'text-ink-gray-5' : 'text-red-600 font-medium'">{{ item.value }}</span>
              </div>
            </div>

            <div v-if="!isFormValid" class="flex items-start gap-2.5 rounded-md bg-surface-yellow-1 border border-outline-yellow-1 px-4 py-3">
              <FeatherIcon name="alert-triangle" class="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
              <p class="text-p-sm text-yellow-700">{{ __('Please fix the items above before submitting.') }}</p>
            </div>

            <Button
              variant="solid"
              :label="submitting ? __('Submitting…') : __('Submit for Verification')"
              iconLeft="send"
              :loading="submitting"
              :disabled="!isFormValid || submitting"
              class="w-full"
              @click="submitVerification"
            />
          </div>

          <!-- Navigation -->
          <div class="flex flex-col gap-2 pt-2 border-t border-outline-gray-2">
            <!-- Inline step error -->
            <div
              v-if="stepError && activeSection < sections.length - 1"
              class="flex items-start gap-2 rounded-md bg-surface-red-1 border border-outline-red-1 px-3 py-2"
            >
              <FeatherIcon name="alert-circle" class="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
              <p class="text-p-sm text-red-700">{{ stepError }}</p>
            </div>

            <div class="flex items-center justify-between">
              <Button v-if="activeSection > 0" variant="subtle" :label="__('Previous')" iconLeft="arrow-left" @click="goPrev" />
              <div v-else></div>
              <Button v-if="activeSection < sections.length - 1" variant="solid" :label="__('Next')" iconRight="arrow-right" @click="goNext" />
            </div>
          </div>

        </template>
      </div>

      <!-- Logout -->
      <div class="px-8 pb-6 pt-2">
        <Button
          variant="outline"
          :label="__('Logout')"
          iconLeft="log-out"
          class="w-full text-red-600 border-outline-red-1 hover:bg-surface-red-1"
          :loading="logout.loading"
          @click="logout.submit()"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { agentStore } from '@/stores/agent'
import { agencyStore } from '@/stores/agency'
import { sessionStore } from '@/stores/session'
import PhoneInput from '@/components/PhoneInput.vue'
import { FeatherIcon, Button, TextInput, FileUploader, Badge, createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

const { agentResource } = agentStore()
const agency = agencyStore()
const { context: agencyContext } = storeToRefs(agency)
const { logout } = sessionStore()
const router = useRouter()

const showAgencyOnboardingLink = computed(
  () => Boolean(agencyContext.value?.agency && agencyContext.value?.can_manage_billing),
)

function goAgencyOnboarding() {
  router.push({ name: 'Agency Onboarding', query: { resume: 'agency' } })
}

const activeSection = ref(0)
const submitting = ref(false)
const mandatoryDocTypes = ref([])
const stepError = ref('')

const sections = [
  { label: 'Basic Info' },
  { label: 'Documents' },
  { label: 'Schedule' },
  { label: 'Submit' },
]

const weekDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const localStatus = computed(() => agentResource.data?.status || 'Draft')
const agencyStatus = computed(() => agencyContext.value?.verification_status || 'Verified')

const formData = ref({
  dfd_registration_id: '',
  brn_id: '',
  phone: '',
  whatsapp_number: '',
  bio: '',
  zone_name: '',
  max_daily_appointments: 10,
  max_appointment_minutes: 30,
  availability_slots: [],
  kyc_documents: [],
})

watch(
  () => agentResource.data,
  (d) => {
    if (!d) return
    formData.value = {
      dfd_registration_id: d.dfd_registration_id || '',
      brn_id: d.brn_id || '',
      phone: d.phone || '',
      whatsapp_number: d.whatsapp_number || '',
      bio: d.bio || '',
      zone_name: d.zone_name || '',
      max_daily_appointments: d.max_daily_appointments || 10,
      max_appointment_minutes: d.max_appointment_minutes || 30,
      availability_slots: d.availability_slots ? [...d.availability_slots] : [],
      kyc_documents: d.kyc_documents ? [...d.kyc_documents] : [],
    }
    // If rejected, go directly to documents tab
    if (d.status === 'Rejected' && rejectedDocs.value.length > 0) {
      activeSection.value = 1
    }
  },
  { immediate: true, deep: true }
)

// Load mandatory doc types from settings
const mandatorySettingsResource = createResource({
  url: 'crm.fcrm.doctype.agent.agent.get_mandatory_kyc_doc_types',
  onSuccess(data) {
    mandatoryDocTypes.value = data || []
  },
})
onMounted(() => mandatorySettingsResource.fetch())

// — Navigation with validation —
function goToCRM() { router.push({ name: 'Home' }) }

/**
 * Validate the current step and return an error string or ''.
 * Step 0 = Basic Info, Step 1 = Documents, Step 2 = Schedule (optional)
 */
function validateCurrentStep() {
  if (activeSection.value === 0) {
    if (!formData.value.dfd_registration_id?.trim()) {
      return 'DLD Registration ID is required before proceeding.'
    }
  }
  if (activeSection.value === 1) {
    if (formData.value.kyc_documents.length === 0) {
      return 'Please upload at least one document before proceeding.'
    }
    if (formData.value.kyc_documents.some(d => !d.document_type)) {
      return 'Please select a document type for every uploaded file.'
    }
    const missing = missingMandatory.value
    if (missing.length > 0) {
      return `Missing mandatory document type(s): ${missing.join(', ')}.`
    }
  }
  return ''
}

function goNext() {
  stepError.value = validateCurrentStep()
  if (stepError.value) return
  stepError.value = ''
  activeSection.value++
}

function goPrev() {
  stepError.value = ''
  activeSection.value--
}

function tryGoToStep(idx) {
  // Allow going back freely; validate before jumping forward
  if (idx <= activeSection.value) {
    stepError.value = ''
    activeSection.value = idx
    return
  }
  // Validate every step in between
  const savedSection = activeSection.value
  for (let s = activeSection.value; s < idx; s++) {
    activeSection.value = s
    const err = validateCurrentStep()
    if (err) {
      activeSection.value = s
      stepError.value = err
      return
    }
  }
  activeSection.value = idx
  stepError.value = ''
}
// Clear the step error as soon as the user makes any relevant change
watch(
  () => [
    formData.value.dfd_registration_id,
    formData.value.kyc_documents.length,
    formData.value.kyc_documents.map(d => d.document_type).join(','),
  ],
  () => { stepError.value = '' }
)


const isDayEnabled = (day) => formData.value.availability_slots.some(s => s.day_of_week === day)

const getFirstSlotForDay = (day) => {
  return formData.value.availability_slots.find(s => s.day_of_week === day) || {}
}

const toggleDay = (day) => {
  if (isDayEnabled(day)) {
    formData.value.availability_slots = formData.value.availability_slots.filter(s => s.day_of_week !== day)
  } else {
    formData.value.availability_slots.push({ day_of_week: day, start_time: '09:00:00', end_time: '17:00:00' })
  }
}

// — Document helpers —
const rejectedDocs = computed(() => formData.value.kyc_documents.filter(d => d.doc_status === 'Rejected'))
const hasDocType = (type) => formData.value.kyc_documents.some(d => d.document_type === type)
const getFileName = (url) => (url || '').split('/').pop() || 'Document'

const statusTheme = (status) => {
  if (status === 'Approved') return 'green'
  if (status === 'Rejected') return 'red'
  return 'gray'
}

const validateIsDocument = (file) => {
  if (!['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'].includes(file.type))
    return 'Only PDF and images are allowed'
}

const validateIsImage = (file) => {
  if (!['image/jpeg', 'image/png', 'image/jpg'].includes(file.type))
    return 'Only JPG and PNG images are allowed'
}

const handleDocumentUpload = (file) => {
  formData.value.kyc_documents.push({ document_file: file.file_url, document_type: '', doc_status: 'Pending', verified: 0 })
}

const triggerRejectedReupload = (doc) => {
  // Remove rejected doc so user can re-upload a fresh one of the same type
  const idx = formData.value.kyc_documents.findIndex(d => d === doc)
  if (idx !== -1) formData.value.kyc_documents.splice(idx, 1)
  document.getElementById('kyc-uploader-trigger')?.click()
}

const removeDoc = (idx) => formData.value.kyc_documents.splice(idx, 1)

// — Validation —
const missingMandatory = computed(() => {
  return mandatoryDocTypes.value.filter(t => !hasDocType(t))
})

const isFormValid = computed(() => {
  if (!formData.value.dfd_registration_id) return false
  if (formData.value.kyc_documents.length === 0) return false
  if (formData.value.kyc_documents.some(d => !d.document_type)) return false
  if (missingMandatory.value.length > 0) return false
  return true
})

const reviewItems = computed(() => [
  {
    label: 'DLD Registration ID',
    ok: !!formData.value.dfd_registration_id,
    value: formData.value.dfd_registration_id || 'Missing — required',
  },
  {
    label: 'Documents uploaded',
    ok: formData.value.kyc_documents.length > 0,
    value: formData.value.kyc_documents.length > 0 ? `${formData.value.kyc_documents.length} file(s)` : 'None — required',
  },
  {
    label: 'Document types assigned',
    ok: formData.value.kyc_documents.length > 0 && !formData.value.kyc_documents.some(d => !d.document_type),
    value: formData.value.kyc_documents.some(d => !d.document_type) ? 'Some missing type' : 'All assigned',
  },
  {
    label: 'Mandatory doc types',
    ok: missingMandatory.value.length === 0,
    value: missingMandatory.value.length === 0
      ? 'All covered'
      : `Missing: ${missingMandatory.value.join(', ')}`,
  },
  {
    label: 'Availability slots',
    ok: true,
    value: `${formData.value.availability_slots.length} day(s) set`,
  },
])

// — Submit —
const submitResource = createResource({
  url: 'frappe.client.set_value',
  makeParams() {
    return {
      doctype: 'Agent',
      name: agentResource.data.name,
      fieldname: { status: 'Pending Verification', ...formData.value },
    }
  },
  onSuccess() {
    toast.success('Submitted for verification!')
    agentResource.reload()
    activeSection.value = 0
  },
  onError(err) {
    toast.error(err.messages?.[0] || 'Submission failed')
  },
})

function submitVerification() {
  if (!formData.value.dfd_registration_id) { toast.error('DLD Registration ID is required'); activeSection.value = 0; return }
  if (formData.value.kyc_documents.length === 0) { toast.error('Please upload at least one document'); activeSection.value = 1; return }
  if (formData.value.kyc_documents.some(d => !d.document_type)) { toast.error('Select a type for each document'); activeSection.value = 1; return }
  if (missingMandatory.value.length > 0) { toast.error(`Missing mandatory docs: ${missingMandatory.value.join(', ')}`); activeSection.value = 1; return }
  submitting.value = true
  submitResource.submit().finally(() => { submitting.value = false })
}
</script>
