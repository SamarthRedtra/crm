<template>
  <div
    v-if="items.length && !dismissed"
    class="flex shrink-0 items-start gap-3 border-b border-amber-200 bg-amber-50 px-4 py-3 text-ink-gray-8"
  >
    <FeatherIcon name="alert-triangle" class="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
    <div class="min-w-0 flex-1">
      <p class="text-p-sm font-medium text-amber-950">
        {{ __('Action required to use the CRM with full access') }}
      </p>
      <ul class="mt-2 list-inside list-disc space-y-1 text-p-sm text-amber-950/90">
        <li v-for="item in items" :key="item.key">
          <button
            type="button"
            class="text-left font-medium text-blue-700 underline decoration-blue-400/60 hover:text-blue-800"
            @click="go(item)"
          >
            {{ item.label }}
          </button>
          <span v-if="item.detail" class="text-ink-gray-6"> — {{ item.detail }}</span>
        </li>
      </ul>
    </div>
    <button
      type="button"
      class="shrink-0 rounded-md px-2 py-1 text-p-xs font-medium text-ink-gray-6 hover:bg-amber-100 hover:text-ink-gray-8"
      :title="__('Dismiss for this session')"
      @click="dismissed = true"
    >
      {{ __('Dismiss') }}
    </button>
  </div>
</template>

<script setup>
import { useSaasPendingItems } from '@/composables/saasPendingItems'
import { FeatherIcon } from 'frappe-ui'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { items } = useSaasPendingItems()
const dismissed = ref(false)

function go(item) {
  if (item.to) {
    router.push(item.to)
  }
}
</script>
