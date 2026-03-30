<template>
  <div class="flex border-b pr-5">
    <div id="app-header" class="flex-1"></div>
    <div class="flex items-center justify-center gap-1">
      <SaaSStatusCenter />
      <CallUI />
    </div>
  </div>
</template>

<script setup>
import CallUI from '@/components/Telephony/CallUI.vue'
import SaaSStatusCenter from '@/components/Layouts/SaaSStatusCenter.vue'
</script>
