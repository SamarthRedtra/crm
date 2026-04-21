<template>
  <Popover v-if="statusItems.length" v-model:show="open">
    <template #target="{ togglePopover }">
      <button
        type="button"
        class="relative mr-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-outline-gray-2 bg-surface-white text-ink-gray-7 hover:bg-surface-gray-2"
        :title="__('Account status')"
        @click="togglePopover"
      >
        <FeatherIcon name="bell" class="h-5 w-5" />
        <span
          class="absolute -right-0.5 -top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold leading-none text-white"
        >
          {{ statusItems.length }}
        </span>
      </button>
    </template>
    <div class="w-72 p-2">
      <p class="px-2 pb-2 text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __('Account status') }}
      </p>
      <button
        v-for="item in statusItems"
        :key="item.key"
        type="button"
        class="w-full rounded-md px-2 py-2.5 text-left text-p-sm text-ink-gray-8 hover:bg-surface-gray-2"
        @click="runItem(item)"
      >
        <span class="font-medium">{{ item.label }}</span>
        <span v-if="item.detail" class="mt-0.5 block text-p-xs text-ink-gray-5">{{ item.detail }}</span>
      </button>
    </div>
  </Popover>
</template>

<script setup>
import { useSaasPendingItems } from '@/composables/saasPendingItems'
import { FeatherIcon, Popover } from 'frappe-ui'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const open = ref(false)
const { items: statusItems } = useSaasPendingItems()

function runItem(item) {
  open.value = false
  if (item.to) {
    router.push(item.to)
  }
}
</script>
