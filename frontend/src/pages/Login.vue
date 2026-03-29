<template>
  <div class="flex min-h-screen w-screen items-center justify-center bg-surface-gray-2 p-4">
    <div class="w-full max-w-md rounded-xl border border-outline-gray-2 bg-surface-white p-6 shadow-sm">
      <div class="mb-6">
        <div v-if="brandResource.data?.brand_logo" class="mb-3">
          <img
            :src="brandResource.data.brand_logo"
            :alt="displayBrandName"
            class="h-12 w-auto max-w-[220px] object-contain object-left"
          />
        </div>
        <p
          v-else
          class="text-xs font-semibold uppercase tracking-wider text-blue-600"
        >
          {{ displayBrandName }}
        </p>
        <h1 class="mt-2 text-2xl font-semibold text-ink-gray-9">{{ __('Sign in') }}</h1>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Access your agency workspace and onboarding status.') }}
        </p>
      </div>

      <form class="flex flex-col gap-4" @submit.prevent="submitLogin">
        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Email') }}</label>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="username"
            required
            class="w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            placeholder="you@agency.com"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-p-sm font-medium text-ink-gray-7">{{ __('Password') }}</label>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            required
            class="w-full rounded border border-outline-gray-2 bg-surface-white px-3 py-2 text-p-sm text-ink-gray-8 outline-none transition focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
            placeholder="********"
          />
        </div>

        <Button
          variant="solid"
          :loading="isSubmitting"
          :label="isSubmitting ? __('Signing in...') : __('Sign in')"
          type="submit"
        />
      </form>

      <div v-if="providersResource.data?.length" class="mt-5">
        <div class="mb-3 flex items-center gap-2">
          <div class="h-px flex-1 bg-outline-gray-2" />
          <span class="text-xs text-ink-gray-4">{{ __('or continue with') }}</span>
          <div class="h-px flex-1 bg-outline-gray-2" />
        </div>
        <div class="flex flex-col gap-2">
          <Button
            v-for="provider in providersResource.data"
            :key="provider.name"
            variant="subtle"
            :label="__('Continue with {0}', [provider.provider_name])"
            @click="redirectToProvider(provider)"
          />
        </div>
      </div>

      <ErrorMessage class="mt-4" :message="errorMessage" />

      <div class="mt-6 rounded-lg border border-outline-blue-1 bg-surface-blue-1 p-3">
        <p class="text-p-sm font-medium text-ink-gray-8">{{ __('New agency?') }}</p>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ __('Register your agency account and start onboarding without existing login access.') }}
        </p>
        <Button class="mt-3" variant="outline" :label="__('Register Agency')" @click="router.push({ name: 'Register Agency' })" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { sessionStore } from '@/stores/session'
import { Button, ErrorMessage, createResource } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { login } = sessionStore()

const form = reactive({
  email: '',
  password: '',
})

const isSubmitting = ref(false)
const errorMessage = ref('')

const brandResource = createResource({
  url: 'crm.api.auth.public_brand',
  auto: true,
  onError() {
    // Branding is optional; fall back to default title.
  },
})

const displayBrandName = computed(() => {
  const name = brandResource.data?.brand_name?.trim()
  return name || __('Redtra CRM')
})

const providersResource = createResource({
  url: 'crm.api.auth.oauth_providers',
  auto: true,
  onError() {
    // Social login is optional; avoid blocking password login.
  },
})

async function submitLogin() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await login.submit({
      usr: form.email,
      pwd: form.password,
    })
  } catch (error) {
    errorMessage.value = error?.message || __('Unable to login. Please check your credentials.')
  } finally {
    isSubmitting.value = false
  }
}

function redirectToProvider(provider) {
  if (!provider?.auth_url) return
  window.location.href = provider.auth_url
}
</script>
