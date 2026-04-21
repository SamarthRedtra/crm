<template>
  <FrappeUIProvider>
    <Layout class="isolate" v-if="session().isLoggedIn">
      <router-view :key="$route.fullPath"/>
    </Layout>
    <Dialogs />
  </FrappeUIProvider>
</template>

<script setup>
import { Dialogs } from '@/utils/dialogs'
import { sessionStore as session } from '@/stores/session'
import { FrappeUIProvider, setConfig } from 'frappe-ui'
import { usePropertySettings } from '@/stores/propertySettings'
import { computed, defineAsyncComponent, onMounted } from 'vue'

const { reload: reloadPropertySettings } = usePropertySettings()

onMounted(() => {
  if (session().isLoggedIn) {
    reloadPropertySettings()
  }
})

const MobileLayout = defineAsyncComponent(
  () => import('./components/Layouts/MobileLayout.vue'),
)
const DesktopLayout = defineAsyncComponent(
  () => import('./components/Layouts/DesktopLayout.vue'),
)
const Layout = computed(() => {
  if (window.innerWidth < 640) {
    return MobileLayout
  } else {
    return DesktopLayout
  }
})

setConfig('systemTimezone', window.timezone?.system || null)
setConfig('localTimezone', window.timezone?.user || null)
</script>
