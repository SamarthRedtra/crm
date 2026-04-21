<template>
  <SettingsPage
    doctype="Agency Billing Settings"
    :title="__('Agency Billing Settings')"
    :successMessage="__('Agency billing settings updated successfully')"
  />
</template>

<script setup>
import SettingsPage from '@/components/Settings/SettingsPage.vue'
</script>
