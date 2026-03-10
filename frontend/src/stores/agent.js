import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

export const agentStore = defineStore('crm-agent', () => {
  const agentResource = createResource({
    url: 'crm.api.doc.get_current_agent',
    cache: 'Agent',
  })

  return {
    agentResource,
  }
})
