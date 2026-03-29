import { createRouter, createWebHistory } from 'vue-router'
import { userResource } from '@/stores/user'
import { sessionStore } from '@/stores/session'
import { viewsStore } from '@/stores/views'

const routes = [
  {
    path: '/login',
    name: 'CRM Login',
    meta: { publicAuthPage: true, allowGuest: true },
    component: () => import('@/pages/Login.vue'),
  },
  {
    alias: ['/signup', '/register'],
    path: '/register-agency',
    name: 'Register Agency',
    meta: { publicAuthPage: true, allowGuest: true },
    component: () => import('@/pages/RegisterAgency.vue'),
  },
  {
    path: '/',
    name: 'Home',
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/pages/MobileNotification.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },
  {
    alias: '/leads',
    path: '/leads/view/:viewType?',
    name: 'Leads',
    component: () => import('@/pages/Leads.vue'),
  },
  {
    path: '/leads/:leadId',
    name: 'Lead',
    component: () => import(`@/pages/${handleMobileView('Lead')}.vue`),
    props: true,
  },
  {
    alias: '/deals',
    path: '/deals/view/:viewType?',
    name: 'Deals',
    component: () => import('@/pages/Deals.vue'),
  },
  {
    path: '/deals/:dealId',
    name: 'Deal',
    component: () => import(`@/pages/${handleMobileView('Deal')}.vue`),
    props: true,
  },
  {
    alias: '/notes',
    path: '/notes/view/:viewType?',
    name: 'Notes',
    component: () => import('@/pages/Notes.vue'),
  },
  {
    alias: '/tasks',
    path: '/tasks/view/:viewType?',
    name: 'Tasks',
    component: () => import('@/pages/Tasks.vue'),
  },
  {
    alias: '/contacts',
    path: '/contacts/view/:viewType?',
    name: 'Contacts',
    component: () => import('@/pages/Contacts.vue'),
  },
  {
    path: '/contacts/:contactId',
    name: 'Contact',
    component: () => import(`@/pages/${handleMobileView('Contact')}.vue`),
    props: true,
  },
  {
    alias: '/organizations',
    path: '/organizations/view/:viewType?',
    name: 'Organizations',
    component: () => import('@/pages/Organizations.vue'),
  },
  {
    path: '/organizations/:organizationId',
    name: 'Organization',
    component: () => import(`@/pages/${handleMobileView('Organization')}.vue`),
    props: true,
  },
  {
    alias: '/call-logs',
    path: '/call-logs/view/:viewType?',
    name: 'Call Logs',
    component: () => import('@/pages/CallLogs.vue'),
  },
  {
    path: '/calendar',
    name: 'Calendar',
    component: () => import('@/pages/Calendar.vue'),
  },
  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    alias: '/properties',
    path: '/properties/view/:viewType?',
    name: 'Properties',
    component: () => import('@/pages/Properties.vue'),
  },
  {
    path: '/properties/:propertyId',
    name: 'Property',
    component: () => import(`@/pages/${handleMobileView('Property')}.vue`),
    props: true,
  },
  {
    path: '/data-import',
    name: 'DataImportList',
    component: () => import('@/pages/DataImport.vue'),
  },
  {
    path: '/data-import/:doctype/:importName?',
    name: 'Data Import',
    component: () => import('@/pages/DataImport.vue'),
  },
  {
    path: '/data-imports/:importName',
    name: 'DataImport',
    component: () => import('@/pages/DataImport.vue'),
  },
  {
    path: '/agents/:agentId',
    name: 'Agent',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    path: '/agencies/:agencyId',
    name: 'Agency',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    path: '/onboarding',
    name: 'Agent Onboarding',
    component: () => import('@/pages/AgentOnboarding.vue'),
  },
  {
    alias: ['/agency_onboarding', '/agency-onboarding'],
    path: '/agencies/onboarding',
    name: 'Agency Onboarding',
    component: () => import('@/pages/AgencyOnboarding.vue'),
  },
  {
    alias: ['/agency_verification', '/agency-verification'],
    path: '/agencies/verification',
    name: 'Agency Verification',
    component: () => import('@/pages/AgencyVerification.vue'),
  },
  {
    alias: ['/billing_activation', '/billing-activation'],
    path: '/agencies/billing-activation',
    name: 'Billing Activation',
    component: () => import('@/pages/BillingActivation.vue'),
  },
  {
    path: '/:invalidpath',
    name: 'Invalid Page',
    component: () => import('@/pages/InvalidPage.vue'),
  },
]

const handleMobileView = (componentName) => {
  return window.innerWidth < 768 ? `Mobile${componentName}` : componentName
}

let router = createRouter({
  history: createWebHistory('/crm'),
  routes,
})

import { agentStore } from '@/stores/agent'
import { agencyStore } from '@/stores/agency'

router.beforeEach(async (to, from, next) => {
  const { isLoggedIn } = sessionStore()
  const isGuestAllowedRoute = Boolean(to.meta?.allowGuest)

  // If sid is in URL and not logged in, use set-session-from-sid to establish session
  const sidFromUrl = to.query.sid || (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('sid'))
  if (!isLoggedIn && sidFromUrl) {
    const redirect = (typeof window !== 'undefined' && window.location.pathname) || '/crm'
    window.location.href = `/api/auth/set-session-from-sid?sid=${encodeURIComponent(sidFromUrl)}&redirect=${encodeURIComponent(redirect)}`
    return
  }

  if (!isLoggedIn && isGuestAllowedRoute) {
    next()
    return
  }

  isLoggedIn && (await userResource.promise)

  if (isLoggedIn && to.meta?.publicAuthPage) {
    next({ name: 'Home' })
    return
  }

  if (isLoggedIn) {
    const { agentResource } = agentStore()
    const {
      contextResource,
      needsAgencyVerification,
      needsAgencyOnboarding,
      needsBillingActivation,
    } = agencyStore()

    if (!contextResource.data) {
      try {
        await contextResource.reload()
      } catch {
        // Keep navigation resilient for non-agency users.
      }
    }

    const routingName = String(to.name || '')
    const bypassRoutes = new Set(['Agency Verification', 'Billing Activation', 'Logout'])

    if (needsAgencyVerification() && routingName !== 'Agency Verification') {
      next({ name: 'Agency Verification' })
      return
    }

    if (!needsAgencyVerification() && routingName === 'Agency Verification') {
      next({ name: 'Home' })
      return
    }

    if (!agentResource.data) {
      await agentResource.reload()
    }
    const isUnverifiedAgent = agentResource.data && agentResource.data.name && agentResource.data.status !== 'Verified'

    if (isUnverifiedAgent && to.name !== 'Agent Onboarding' && !bypassRoutes.has(routingName)) {
      next({ name: 'Agent Onboarding' })
      return
    }

    if (!isUnverifiedAgent && to.name === 'Agent Onboarding') {
      next({ name: 'Home' })
      return
    }

    if (!needsAgencyVerification() && needsAgencyOnboarding() && routingName !== 'Agency Onboarding') {
      next({ name: 'Agency Onboarding' })
      return
    }

    if (!needsAgencyVerification() && !needsAgencyOnboarding() && routingName === 'Agency Onboarding') {
      next({ name: 'Home' })
      return
    }

    if (
      !needsAgencyVerification() &&
      !needsAgencyOnboarding() &&
      needsBillingActivation() &&
      routingName !== 'Billing Activation'
    ) {
      next({ name: 'Billing Activation' })
      return
    }

    if (!needsBillingActivation() && routingName === 'Billing Activation') {
      next({ name: 'Home' })
      return
    }
  }

  if (to.name === 'Home' && isLoggedIn) {
    const { views, getDefaultView } = viewsStore()
    await views.promise

    let defaultView = getDefaultView()
    if (!defaultView) {
      next({ name: 'Dashboard' })
      return
    }

    let { route_name, type, name, is_standard } = defaultView
    route_name = route_name || 'Leads'

    if (name && !is_standard) {
      next({ name: route_name, params: { viewType: type }, query: { view: name } })
    } else {
      next({ name: route_name, params: { viewType: type } })
    }
  } else if (!isLoggedIn) {
    next({ name: 'CRM Login', query: { redirect: to.fullPath || '/dashboard' } })
  } else if (to.matched.length === 0) {
    next({ name: 'Invalid Page' })
  } else if (['Deal', 'Lead', 'Property'].includes(to.name) && !to.hash) {
    let storageKey = `last${to.name}Tab`
    const activeTab = localStorage.getItem(storageKey) || 'activity'
    const hash = '#' + activeTab
    next({ name: to.name, params: to.params, query: to.query, hash })
  } else {
    next()
  }
})

export default router
