import { createDocumentResource, call } from 'frappe-ui'
import { ref } from 'vue'

const propertySettings = ref({})
const fieldConfigs = ref({})

const _propertySettings = createDocumentResource({
  doctype: 'Property Setting',
  name: 'Property Setting',
  onSuccess: (data) => {
    propertySettings.value = data
    fetchFieldConfigs()
  },
})

async function fetchFieldConfigs() {
  const data = await call('crm.fcrm.doctype.fcrm_settings.fcrm_settings.get_field_configs')
  fieldConfigs.value = data
}

export function usePropertySettings() {
  return {
    propertySettings,
    fieldConfigs,
    reload: () => {
      _propertySettings.reload()
    },
  }
}
