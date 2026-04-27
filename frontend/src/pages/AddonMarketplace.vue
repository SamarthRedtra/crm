<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-gray-1">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="Addon Marketplace" />
      </template>
    </LayoutHeader>
    <div class="flex-1 overflow-y-auto">
      <div class="addon-marketplace">
    <!-- Header -->
    <header class="addon-header">
      <div class="addon-header-content">
        <div class="addon-header-text">
          <h1 class="addon-title">{{ __('Addon Marketplace') }}</h1>
          <p class="addon-subtitle">
            {{ __('Enhance your agency with premium add-ons to unlock powerful features.') }}
          </p>
        </div>
        <div v-if="billingStatus" class="addon-header-badge">
          <Badge
            :label="billingStatus"
            variant="subtle"
            :theme="billingStatus === 'Active' ? 'green' : 'orange'"
          />
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="addonStatus.loading" class="addon-loading">
      <LoadingIndicator class="size-8" />
      <p class="addon-loading-text">{{ __('Loading addons...') }}</p>
    </div>

    <!-- Content -->
    <template v-else-if="data?.addons?.length">
      <!-- Available Addons Grid -->
      <section class="addon-section">
        <h2 class="addon-section-title">{{ __('Available Add-ons') }}</h2>
        <div class="addon-grid">
          <div
            v-for="addon in data.addons"
            :key="addon.name"
            class="addon-card"
            :class="{
              'addon-card--active': addon.is_active,
              'addon-card--paid': addon.requires_upfront_payment && !addon.is_active,
            }"
          >
            <!-- Card header with icon -->
            <div class="addon-card-header">
              <div class="addon-card-icon" :class="getIconClass(addon)">
                <FeatherIcon :name="getIconName(addon)" class="size-5" />
              </div>
              <Badge
                v-if="addon.is_active"
                :label="__('Active')"
                variant="subtle"
                theme="green"
                class="addon-card-status"
              />
              <Badge
                v-else-if="addon.requires_upfront_payment"
                :label="__('Premium')"
                variant="subtle"
                theme="orange"
                class="addon-card-status"
              />
              <Badge
                v-else
                :label="__('Free to Activate')"
                variant="subtle"
                theme="blue"
                class="addon-card-status"
              />
            </div>

            <!-- Card body -->
            <div class="addon-card-body">
              <h3 class="addon-card-name">{{ addon.addon_name }}</h3>
              <p v-if="addon.description" class="addon-card-desc">
                {{ addon.description }}
              </p>
              <div class="addon-card-meta">
                <span class="addon-card-model">{{ addon.pricing_model }}</span>
                <span v-if="addon.unit_label" class="addon-card-unit">
                  · {{ addon.unit_label }}
                </span>
              </div>
            </div>

            <!-- Pricing -->
            <div class="addon-card-pricing">
              <span class="addon-card-rate">
                {{ formatRate(addon.rate, addon.currency) }}
              </span>
              <span class="addon-card-period">
                /{{ addon.pricing_model === 'Daily Fixed' ? __('day') : addon.pricing_model === 'Monthly Fixed' ? __('month') : __('unit') }}
              </span>
            </div>

            <!-- Actions -->
            <div class="addon-card-actions">
              <!-- Already active -->
              <template v-if="addon.is_active">
                <Button
                  variant="subtle"
                  theme="red"
                  :label="__('Deactivate')"
                  :loading="processingAddon === addon.name && actionType === 'deactivate'"
                  class="addon-btn addon-btn--deactivate"
                  @click="confirmDeactivate(addon)"
                />
              </template>

              <!-- Requires payment -->
              <template v-else-if="addon.requires_upfront_payment">
                <Button
                  variant="solid"
                  :label="__('Purchase — Pay Now')"
                  :loading="processingAddon === addon.name && actionType === 'purchase'"
                  class="addon-btn addon-btn--purchase"
                  @click="purchaseAddon(addon)"
                />
              </template>

              <!-- Free activation -->
              <template v-else>
                <Button
                  variant="solid"
                  :label="__('Activate')"
                  :loading="processingAddon === addon.name && actionType === 'activate'"
                  class="addon-btn addon-btn--activate"
                  @click="activateAddon(addon)"
                />
              </template>
            </div>
          </div>
        </div>
      </section>

      <!-- Active Addons Summary -->
      <section v-if="activeAddons.length" class="addon-section addon-active-section">
        <h2 class="addon-section-title">{{ __('Your Active Add-ons') }}</h2>
        <div class="addon-active-list">
          <div
            v-for="addon in activeAddons"
            :key="addon.name"
            class="addon-active-row"
          >
            <div class="addon-active-info">
              <div class="addon-active-icon" :class="getIconClass(addon)">
                <FeatherIcon :name="getIconName(addon)" class="size-4" />
              </div>
              <div>
                <p class="addon-active-name">{{ addon.addon_name }}</p>
                <p class="addon-active-meta">
                  {{ addon.pricing_model }} · {{ formatRate(addon.rate, addon.currency) }}
                </p>
              </div>
            </div>
            <div class="addon-active-actions">
              <Badge :label="__('Active')" variant="subtle" theme="green" />
              <Button
                variant="ghost"
                theme="red"
                size="sm"
                :label="__('Deactivate')"
                :loading="processingAddon === addon.name && actionType === 'deactivate'"
                @click="confirmDeactivate(addon)"
              />
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- Empty state -->
    <div v-else class="addon-empty">
      <FeatherIcon name="package" class="addon-empty-icon" />
      <h3 class="addon-empty-title">{{ __('No Add-ons Available') }}</h3>
      <p class="addon-empty-desc">
        {{ __('There are no billing add-ons configured yet. Contact your CRM administrator.') }}
      </p>
    </div>

    <!-- Deactivation confirm dialog -->
    <Dialog
      v-model="showDeactivateDialog"
      :options="{
        title: __('Deactivate Add-on'),
        size: 'sm',
        actions: [
          {
            label: __('Confirm Deactivate'),
            variant: 'solid',
            theme: 'red',
            onClick: executeDeactivation,
          },
          {
            label: __('Cancel'),
            variant: 'subtle',
            onClick: () => (showDeactivateDialog = false),
          },
        ],
      }"
    >
      <template #body-content>
        <p class="text-p-base text-ink-gray-7">
          {{ __('Are you sure you want to deactivate') }}
          <strong>{{ deactivatingAddon?.addon_name }}</strong>?
          {{ __('Daily charges will stop from the next billing cycle.') }}
        </p>
      </template>
    </Dialog>

    <ErrorMessage :message="errorMessage" />
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'

const route = useRoute()
const router = useRouter()

const errorMessage = ref('')
const processingAddon = ref('')
const actionType = ref('')
const showDeactivateDialog = ref(false)
const deactivatingAddon = ref(null)

const addonStatus = createResource({
  url: 'crm.api.redtra.billing.list_agency_addon_status',
  auto: true,
  onError(error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  },
})

const data = computed(() => addonStatus.data || {})
const billingStatus = computed(() => data.value.billing_status)

const activeAddons = computed(() =>
  (data.value.addons || []).filter((a) => a.is_active),
)

function formatRate(rate, currency) {
  const num = Number(rate || 0)
  return `${num.toFixed(2)} ${currency || ''}`.trim()
}

function getIconName(addon) {
  const name = (addon.addon_name || '').toLowerCase()
  if (name.includes('listing') || name.includes('property')) return 'home'
  if (name.includes('photo') || name.includes('image') || name.includes('gallery')) return 'camera'
  if (name.includes('featured') || name.includes('boost') || name.includes('premium')) return 'star'
  if (name.includes('report') || name.includes('analytics')) return 'bar-chart-2'
  if (name.includes('sms') || name.includes('message')) return 'message-square'
  if (name.includes('email') || name.includes('mail')) return 'mail'
  if (name.includes('calendar') || name.includes('schedule')) return 'calendar'
  return 'package'
}

function getIconClass(addon) {
  if (addon.is_active) return 'addon-icon--active'
  if (addon.requires_upfront_payment) return 'addon-icon--premium'
  return 'addon-icon--free'
}

async function purchaseAddon(addon) {
  processingAddon.value = addon.name
  actionType.value = 'purchase'
  errorMessage.value = ''

  try {
    const response = await call('crm.api.redtra.billing.purchase_addon', {
      addon: addon.name,
      quantity: 1,
    })
    if (response?.url) {
      window.location.href = response.url
    }
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    processingAddon.value = ''
    actionType.value = ''
  }
}

async function activateAddon(addon) {
  processingAddon.value = addon.name
  actionType.value = 'activate'
  errorMessage.value = ''

  try {
    await call('crm.api.redtra.billing.activate_addon', {
      addon: addon.name,
      quantity: 1,
    })
    toast.success(__('Add-on "{0}" activated successfully!', [addon.addon_name]))
    await addonStatus.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    processingAddon.value = ''
    actionType.value = ''
  }
}

function confirmDeactivate(addon) {
  deactivatingAddon.value = addon
  showDeactivateDialog.value = true
}

async function executeDeactivation() {
  const addon = deactivatingAddon.value
  if (!addon) return

  showDeactivateDialog.value = false
  processingAddon.value = addon.name
  actionType.value = 'deactivate'
  errorMessage.value = ''

  try {
    await call('crm.api.redtra.billing.deactivate_addon', {
      addon: addon.name,
    })
    toast.success(__('Add-on "{0}" deactivated.', [addon.addon_name]))
    await addonStatus.reload()
  } catch (error) {
    errorMessage.value = error?.messages?.[0] || error?.message
  } finally {
    processingAddon.value = ''
    actionType.value = ''
    deactivatingAddon.value = null
  }
}

// Handle return from Stripe Checkout
async function handleStripeReturn() {
  const purchaseStatus = route.query.addon_purchase
  const sessionId = route.query.session_id

  if (purchaseStatus === 'success' && sessionId) {
    try {
      const result = await call('crm.api.redtra.billing.complete_addon_purchase', {
        session_id: sessionId,
      })
      if (result?.ok) {
        toast.success(__('Add-on "{0}" purchased and activated!', [result.addon_name]))
      }
    } catch (error) {
      errorMessage.value = error?.messages?.[0] || error?.message
    }
    // Clean up URL query params
    router.replace({ path: '/addons' })
    await addonStatus.reload()
  } else if (purchaseStatus === 'cancel') {
    toast.info(__('Add-on purchase was cancelled.'))
    router.replace({ path: '/addons' })
  }
}

watch(
  () => route.query.addon_purchase,
  () => handleStripeReturn(),
  { immediate: true },
)
</script>

<style scoped>
.addon-marketplace {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
  max-width: 80rem;
  margin: 0 auto;
  min-height: 100%;
}

/* ─── Header ─── */
.addon-header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 1rem;
  padding: 2rem 2.5rem;
  position: relative;
  overflow: hidden;
}

.addon-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 50%;
  height: 200%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.15), transparent 70%);
  pointer-events: none;
}

.addon-header::after {
  content: '';
  position: absolute;
  bottom: -30%;
  left: -10%;
  width: 40%;
  height: 160%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.1), transparent 70%);
  pointer-events: none;
}

.addon-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

.addon-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: -0.02em;
}

.addon-subtitle {
  margin-top: 0.5rem;
  font-size: 0.9375rem;
  color: rgba(255, 255, 255, 0.65);
  max-width: 36rem;
}

/* ─── Loading ─── */
.addon-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 16rem;
  gap: 0.75rem;
}

.addon-loading-text {
  font-size: 0.875rem;
  color: var(--ink-gray-5);
}

/* ─── Sections ─── */
.addon-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.addon-section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--ink-gray-9);
  margin: 0;
}

/* ─── Grid ─── */
.addon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.25rem;
}

/* ─── Card ─── */
.addon-card {
  display: flex;
  flex-direction: column;
  background: var(--surface-white);
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.875rem;
  padding: 1.5rem;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.addon-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--blue-400), var(--blue-500));
  opacity: 0;
  transition: opacity 0.25s ease;
}

.addon-card:hover {
  border-color: var(--outline-blue-2);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06), 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-2px);
}

.addon-card:hover::before {
  opacity: 1;
}

.addon-card--active {
  border-color: var(--green-200);
  background: linear-gradient(180deg, rgba(34, 197, 94, 0.03) 0%, var(--surface-white) 100%);
}

.addon-card--active::before {
  background: linear-gradient(90deg, #22c55e, #16a34a);
  opacity: 1;
}

.addon-card--paid::before {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.addon-card--paid:hover::before {
  opacity: 1;
}

/* Card header */
.addon-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.addon-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  flex-shrink: 0;
}

.addon-icon--active {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #16a34a;
}

.addon-icon--premium {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #d97706;
}

.addon-icon--free {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #2563eb;
}

/* Card body */
.addon-card-body {
  flex: 1;
  margin-bottom: 1rem;
}

.addon-card-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink-gray-9);
  margin: 0 0 0.375rem;
}

.addon-card-desc {
  font-size: 0.8125rem;
  color: var(--ink-gray-5);
  line-height: 1.5;
  margin: 0 0 0.5rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.addon-card-meta {
  font-size: 0.75rem;
  color: var(--ink-gray-4);
}

/* Pricing */
.addon-card-pricing {
  display: flex;
  align-items: baseline;
  gap: 0.25rem;
  margin-bottom: 1.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--outline-gray-1);
}

.addon-card-rate {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ink-gray-9);
  letter-spacing: -0.02em;
}

.addon-card-period {
  font-size: 0.8125rem;
  color: var(--ink-gray-5);
}

/* Actions */
.addon-card-actions {
  display: flex;
  flex-direction: column;
}

.addon-btn {
  width: 100%;
  justify-content: center;
  border-radius: 0.5rem;
  font-weight: 500;
  padding: 0.5rem 1rem;
  min-height: 2.5rem;
}

.addon-btn--purchase {
  background: linear-gradient(135deg, #f59e0b, #d97706) !important;
  color: #fff !important;
  border: none !important;
}

.addon-btn--purchase:hover {
  background: linear-gradient(135deg, #d97706, #b45309) !important;
}

.addon-btn--activate {
  background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
  color: #fff !important;
  border: none !important;
}

.addon-btn--activate:hover {
  background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
}

/* ─── Active Addons Summary ─── */
.addon-active-section {
  background: var(--surface-white);
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.875rem;
  padding: 1.5rem;
}

.addon-active-section .addon-section-title {
  margin-bottom: 0.5rem;
}

.addon-active-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.addon-active-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--surface-gray-1);
  border-radius: 0.625rem;
  transition: background 0.15s ease;
}

.addon-active-row:hover {
  background: var(--surface-gray-2);
}

.addon-active-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.addon-active-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  flex-shrink: 0;
}

.addon-active-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ink-gray-8);
  margin: 0;
}

.addon-active-meta {
  font-size: 0.75rem;
  color: var(--ink-gray-5);
  margin: 0.125rem 0 0;
}

.addon-active-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ─── Empty state ─── */
.addon-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 24rem;
  text-align: center;
  gap: 0.75rem;
}

.addon-empty-icon {
  width: 3rem;
  height: 3rem;
  color: var(--ink-gray-3);
}

.addon-empty-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--ink-gray-7);
  margin: 0;
}

.addon-empty-desc {
  font-size: 0.875rem;
  color: var(--ink-gray-5);
  max-width: 24rem;
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .addon-marketplace {
    padding: 1rem;
    gap: 1.5rem;
  }

  .addon-header {
    padding: 1.5rem;
    border-radius: 0.75rem;
  }

  .addon-title {
    font-size: 1.375rem;
  }

  .addon-header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .addon-grid {
    grid-template-columns: 1fr;
  }
}
</style>
