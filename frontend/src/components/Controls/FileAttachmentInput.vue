<template>
  <div class="flex min-w-0 items-center gap-2">
    <a
      v-if="modelValue"
      :href="modelValue"
      target="_blank"
      class="truncate text-sm text-ink-blue-3 hover:underline"
    >
      {{ fileLabel }}
    </a>
    <span v-else class="truncate text-sm text-ink-gray-4">
      {{ __('No file selected') }}
    </span>
    <FileUploader :file-types="fileTypes" @success="(file) => emit('change', file.file_url)">
      <template #default="{ openFileSelector, uploading, progress }">
        <Button
          variant="ghost"
          class="shrink-0"
          :label="uploading ? __('Uploading {0}%', [progress]) : uploadLabel"
          :iconLeft="uploading ? 'cloud-upload' : 'upload'"
          @click="openFileSelector"
        />
      </template>
    </FileUploader>
    <Button
      v-if="modelValue"
      variant="ghost"
      class="shrink-0"
      icon="x"
      @click="emit('change', '')"
    />
  </div>
</template>

<script setup>
import { FileUploader } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  fileTypes: {
    type: String,
    default: '*',
  },
  uploadLabel: {
    type: String,
    default: 'Attach',
  },
})

const emit = defineEmits(['change'])

const fileLabel = computed(() => {
  if (!props.modelValue) return ''
  return props.modelValue.split('/').pop() || props.modelValue
})
</script>
