import { sessionStore } from '@/stores/session'
import { agentStore } from '@/stores/agent'
import { usePropertySettings } from '@/stores/propertySettings'

const { fieldConfigs } = usePropertySettings()
const session = sessionStore()

const PROPERTY_FIELD_GROUPS = {
  sidebar: [
    {
      name: 'overview',
      label: 'Overview',
      opened: true,
      fields: [
        'title',
        'property_code',
        'listing_type',
        'property_category',
        'property_type',
      ],
    },
    {
      name: 'pricing_specs',
      label: 'Pricing & Specs',
      opened: true,
      fields: [
        'price',
        'currency',
        'bedrooms',
        'bathrooms',
        'area_sqft',
        'furnishing_status',
      ],
    },
    {
      name: 'ownership',
      label: 'Ownership',
      opened: true,
      fields: ['agent', 'developer', 'completion_status', 'off_plan_agencies'],
    },
    {
      name: 'location',
      label: 'Location',
      opened: true,
      fields: ['area', 'city', 'state', 'country', 'pincode'],
    },
    {
      name: 'publishing',
      label: 'Publishing',
      opened: false,
      fields: ['is_featured', 'featured_from', 'featured_until', 'is_sold', 'is_rented', 'views_count'],
    },
  ],
  data: [
    {
      name: 'details_tab',
      label: 'Details',
      sections: [
        {
          name: 'details_section',
          label: 'Details',
          columns: [
            ['title', 'developer', 'agent', 'is_sold', 'is_rented'],
            [
              'property_category',
              'listing_type',
              'rent_type',
              'completion_status',
              'property_code',
              'property_type',
              'off_plan_agencies',
            ],
          ],
        },
        {
          name: 'content_section',
          label: 'Content',
          columns: [['description']],
        },
        {
          name: 'off_plan_section',
          label: 'Off-Plan Details',
          columns: [
            [
              'trakheesi_listing_number',
              'license_number',
              'trakheesi_permit_number',
              'trakheesi_qr_code',
              'zone_name',
              'handover_quarter',
              'handover_year',
            ],
            ['payment_plan_table', 'project_units_table', 'payment_plan_type', 'completion_percentage'],
          ],
        },
      ],
    },
    {
      name: 'pricing_tab',
      label: 'Pricing',
      sections: [
        {
          name: 'pricing_section',
          label: 'Pricing',
          columns: [
            ['price', 'currency'],
            ['bedrooms', 'bathrooms', 'furnishing_status', 'area_sqft'],
          ],
        },
      ],
    },
    {
      name: 'amenities_tab',
      label: 'Amenities',
      sections: [
        {
          name: 'amenities_section',
          label: 'Amenities',
          columns: [['amenities']],
        },
      ],
    },
    {
      name: 'location_tab',
      label: 'Location',
      sections: [
        {
          name: 'location_section',
          label: 'Location',
          columns: [
            ['area', 'address_line1', 'address_line2', 'city', 'state', 'country', 'pincode'],
            ['latitude', 'longitude'],
          ],
        },
      ],
    },
    {
      name: 'media_tab',
      label: 'Media',
      sections: [
        {
          name: 'media_section',
          label: 'Media',
          columns: [['primary_image', 'gallery'], ['views_count']],
        },
      ],
    },
    {
      name: 'featured_tab',
      label: 'Featured',
      sections: [
        {
          name: 'featured_section',
          label: 'Featured Details',
          columns: [['is_featured'], ['featured_from', 'featured_until']],
        },
      ],
    },
    {
      name: 'admin_tab',
      label: 'Admin Details',
      sections: [
        {
          name: 'admin_section',
          label: 'Quality Scoring',
          columns: [['quality_score']],
        },
      ],
    },
  ],
  quickEntry: [
    {
      name: 'details_tab',
      label: 'Details',
      sections: [
        {
          name: 'details_section',
          label: 'Basic Information',
          hideLabel: true,
          columns: [
            [
              'title',
              'developer',
              'agent',
              'property_category',
              'trakheesi_listing_number',
              'trakheesi_permit_number',
              'is_featured',
            ],
            [
              'property_type',
              'rent_type',
              'property_code',
              'license_number',
              'trakheesi_qr_code',
              'featured_from',
              'featured_until',
            ],
          ],
        },
        {
          name: 'content_section',
          label: 'Content',
          columns: [['description']],
        },
      ],
    },
    {
      name: 'pricing_tab',
      label: 'Pricing',
      sections: [
        {
          name: 'pricing_section',
          label: 'Pricing & Specs',
          hideLabel: true,
          columns: [
            ['price', 'currency', 'furnishing_status', 'is_studio'],
            ['bedrooms', 'bathrooms', 'area_sqft']
          ],
        },
      ],
    },
    {
      name: 'offplan_details_tab',
      label: 'Off-plan details',
      sections: [
        {
          name: 'offplan_section',
          label: 'Off-Plan Details',
          hideLabel: true,
          columns: [
            ['handover_quarter', 'handover_year', 'payment_plan_type', 'completion_percentage'],
            ['payment_plan_table', 'project_units_table'],
          ],
        },
      ],
    },
    {
      name: 'amenities_tab',
      label: 'Amenities',
      sections: [
        {
          name: 'amenities_section',
          label: 'Amenities',
          hideLabel: true,
          columns: [['amenities']],
        },
      ],
    },
    {
      name: 'location_tab',
      label: 'Location',
      sections: [
        {
          name: 'location_section',
          label: 'Location',
          hideLabel: true,
          columns: [
            ['area', 'address_line1', 'state', 'latitude'], 
            ['city', 'address_line2', 'country', 'longitude']
          ],
        },
      ],
    },
    {
      name: 'media_tab',
      label: 'Media',
      sections: [
        {
          name: 'media_section',
          label: 'Media',
          hideLabel: true,
          columns: [['primary_image', 'gallery']],
        },
      ],
    },
  ],
}

export const PROPERTY_RESIDENTIAL_TYPES = [
  'Apartment',
  'Villa',
  'Townhouse',
  'Penthouse',
  'Villa Compound',
  'Hotel Apartment',
  'Land',
  'Floor',
  'Building',
]

export const PROPERTY_COMMERCIAL_TYPES = [
  'Office',
  'Shop',
  'Warehouse',
  'Labour Camp',
  'Villa',
  'Bulk Unit',
  'Land',
  'Floor',
  'Building',
  'Factory',
  'Industrial Land',
  'Mixed Use Land',
  'Showroom',
  'Other Commercial',
]

export const STANDARD_AMENITIES = [
  'Pool',
  'Gym',
  'Parking',
  'Balcony',
  'Sea view',
  '24/7 security',
  'Concierge',
  'Kids area'
]

export const PROPERTY_SIDEBAR_SETTINGS_KEY = 'PropertySidebar'

export const PROPERTY_STATUS_META = {
  Draft: {
    name: 'Draft',
    color: 'text-gray-500',
  },
  'Under Verification': {
    name: 'Under Verification',
    color: 'text-orange-500',
  },
  'Pending DLD': {
    name: 'Pending DLD',
    color: 'text-blue-500',
  },
  'Rejected DLD': {
    name: 'Rejected DLD',
    color: 'text-rose-500',
  },
  Active: {
    name: 'Active',
    color: 'text-green-500',
  },
  Inactive: {
    name: 'Inactive',
    color: 'text-red-500',
  },
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function normalizeSelectOptions(options, field) {
  if (Array.isArray(options)) {
    return clone(options)
  }

  if (typeof options !== 'string') {
    return options
  }

  let values = options.split('\n').map((value) => value.trim())
  values = values.filter((value) => value || field?.reqd !== 1)

  if (field?.reqd !== 1 && values[0] !== '') {
    values.unshift('')
  }

  return values.map((value) => ({
    label: value,
    value,
  }))
}

function createFieldMap(metaFields = []) {
  return metaFields.reduce((fieldMap, field) => {
    fieldMap[field.fieldname] = clone(field)
    return fieldMap
  }, {})
}

function getField(fieldMap, fieldname, overrides = {}) {
  let field = fieldMap[fieldname]
  if (!field) {
    return null
  }

  field = clone(field)

  // Apply backend field configs
  const config = fieldConfigs.value?.[fieldname]
  if (config) {
    if (config.label) overrides.label = config.label
    if (config.is_mandatory) overrides.reqd = 1
    if (config.is_hidden) overrides.hidden = 1
    if (config.is_read_only) overrides.read_only = 1
  }

  if (field.fieldtype === 'Select') {
    field.options = normalizeSelectOptions(overrides.options || field.options, field)
  }

  return {
    ...field,
    ...overrides,
  }
}

function buildSections(fieldMap, sections) {
  return sections.map((section) => ({
    name: section.name,
    label: section.label,
    opened: section.opened ?? true,
    hideLabel: Boolean(section.hideLabel),
    columns: section.columns.map((column, idx) => ({
      name: `${section.name}_column_${idx + 1}`,
      fields: column.map((fieldname) => getField(fieldMap, fieldname)).filter(Boolean),
    })),
  }))
}

export function getPropertyStatusColor(status) {
  return PROPERTY_STATUS_META[status]?.color || PROPERTY_STATUS_META.Draft.color
}

export function getPropertyStatusMeta(name) {
  return PROPERTY_STATUS_META[name] || PROPERTY_STATUS_META.Draft
}

export function getPropertyTypeOptions(propertyCategory) {
  if (propertyCategory === 'Residential') {
    return PROPERTY_RESIDENTIAL_TYPES
  }

  if (propertyCategory === 'Commercial') {
    return PROPERTY_COMMERCIAL_TYPES
  }

  return [...new Set([...PROPERTY_RESIDENTIAL_TYPES, ...PROPERTY_COMMERCIAL_TYPES])]
}

export function getPropertySidebarSectionNames() {
  return PROPERTY_FIELD_GROUPS.sidebar.map((section) => section.name)
}

export function getPropertySidebarSectionOptions() {
  return PROPERTY_FIELD_GROUPS.sidebar.map((section) => ({
    name: section.name,
    label: section.label,
  }))
}

export function buildPropertySidebarSections(metaFields, options = {}) {
  const fieldMap = createFieldMap(metaFields)
  const visibleSections = options.visibleSections || getPropertySidebarSectionNames()
  // C-03: Detect agent users to make status read-only
  const { agentResource } = agentStore()
  const isAgent = !!(agentResource.data && agentResource.data.name)

  return PROPERTY_FIELD_GROUPS.sidebar
    .filter((section) => visibleSections.includes(section.name))
    .map((section) => ({
      name: section.name,
      label: section.label,
      opened: section.opened ?? true,
      columns: [
        {
          name: `${section.name}_column_1`,
          fields: section.fields
            .map((fieldname) => {
              let overrides = {}

              if (fieldname === 'status') {
                overrides.options = Object.keys(PROPERTY_STATUS_META)
                // C-03: Agents cannot change status
                if (isAgent) {
                  overrides.read_only = 1
                }
              }

              if (fieldname === 'property_type') {
                overrides.options = getPropertyTypeOptions(options.doc?.property_category)
              }

              if (['property_code', 'views_count'].includes(fieldname)) {
                overrides.read_only = 1
              }

              if (fieldname === 'description') {
                overrides.fieldtype = 'Small Text'
              }

              return getField(fieldMap, fieldname, overrides)
            })
            .filter(Boolean),
        },
      ],
    }))
}

export function buildPropertyDataTabs(metaFields, doc = {}) {
  const fieldMap = createFieldMap(metaFields)
  const session = sessionStore()
  const { agentResource } = agentStore()
  const isAgent = !!(agentResource.data && agentResource.data.name)

  return PROPERTY_FIELD_GROUPS.data
    .filter((tab) => {
      if (tab.name === 'featured_tab') {
        return false
      }
      if (tab.name === 'admin_tab' && isAgent) {
        return false
      }
      return true
    })
    .map((tab) => ({
    name: tab.name,
    label: tab.label,
    sections: buildSections(
      fieldMap,
      tab.sections.map((section) => ({
        ...section,
        columns: section.columns.map((column) =>
          column.filter((fieldname) => {
            if (fieldname === 'project_units_table' && session.user !== 'Administrator') {
              return false
            }
            return true
          }).map((fieldname) => {
            if (fieldname === 'property_type') {
              fieldMap.property_type = getField(fieldMap, 'property_type', {
                options: getPropertyTypeOptions(doc.property_category),
              })
              return fieldname
            }

            if (['status', 'is_sold', 'is_rented'].includes(fieldname)) {
              fieldMap[fieldname] = getField(fieldMap, fieldname, {
                read_only: 1,
              })
            }
            return fieldname
          }),
        ),
      })),
    ),
  }))
}

export function buildPropertyQuickEntryTabs(metaFields, doc = {}) {
  const fieldMap = createFieldMap(metaFields)

  if (fieldMap.status) {
    fieldMap.status.options = normalizeSelectOptions(Object.keys(PROPERTY_STATUS_META).join('\n'), {
      reqd: 1,
    })
  }

  if (fieldMap.property_type) {
    fieldMap.property_type.options = normalizeSelectOptions(
      getPropertyTypeOptions(doc.property_category).join('\n'),
      fieldMap.property_type,
    )
  }

  if (fieldMap.property_code) {
    fieldMap.property_code.read_only = 1
    fieldMap.property_code.description = 'Auto-generated after creation'
  }

  if (fieldMap.trakheesi_permit_number) {
    fieldMap.trakheesi_permit_number.reqd = 1
  }

  if (fieldMap.trakheesi_qr_code) {
    fieldMap.trakheesi_qr_code.reqd = 1
  }

  if (fieldMap.featured_from) {
    fieldMap.featured_from.depends_on = 'eval:doc.is_featured == 1'
  }

  if (fieldMap.featured_until) {
    fieldMap.featured_until.depends_on = 'eval:doc.is_featured == 1'
  }

  if (fieldMap.description) {
    fieldMap.description.fieldtype = 'Small Text'
  }

  return PROPERTY_FIELD_GROUPS.quickEntry
    .filter((tab) => {
      if (tab.name === 'offplan_details_tab' && doc.completion_status !== 'Off-Plan') {
        return false
      }
      return true
    })
    .map((tab) => ({
      name: tab.name,
      label: tab.label,
      sections: buildSections(fieldMap, tab.sections),
    }))
}

export function validatePropertyDoc(doc) {
  // Hardcoded validations...
  if (!doc.title) {
    return 'Title is mandatory'
  }

  // Dynamic validations from backend
  for (const fieldname in fieldConfigs.value) {
    const config = fieldConfigs.value[fieldname]
    const value = doc[fieldname]

    if (config.is_mandatory && (!value || value === '')) {
      return `${config.label || fieldname} is mandatory`
    }

    if (typeof value === 'string' && (config.min_words || config.max_words)) {
      const words = value.trim().split(/\s+/).filter(Boolean).length
      if (config.min_words && words < config.min_words) {
        return `${config.label || fieldname} must be at least ${config.min_words} words`
      }
      if (config.max_words && words > config.max_words) {
        return `${config.label || fieldname} must not exceed ${config.max_words} words`
      }
    }
  }

  // Enforce title words if not overridden by backend or in addition to
  const titleLetters = doc.title.replace(/\s+/g, '').length
  if (titleLetters > 50) {
    return 'Title must not exceed 50 letters'
  }

  // C-07: Trakheesi fields mandatory — admin (session.user === 'Administrator') can bypass
  const { agentResource } = agentStore()
  const isAgent = !!(agentResource.data && agentResource.data.name)

  if (doc.is_featured) {
    if (!doc.featured_from) return 'Featured From is mandatory'
    if (!doc.featured_until) return 'Featured Until is mandatory'
  }

  // Force Trakheesi fields mandatory in Vue CRM
  if (!doc.trakheesi_permit_number) {
    return 'Trakheesi Permit Number is mandatory'
  }

  if (!doc.trakheesi_qr_code) {
    return 'Trakheesi QR Code is mandatory'
  }

  if (doc.property_category) {
    let allowedTypes = getPropertyTypeOptions(doc.property_category)
    if (!allowedTypes.includes(doc.property_type)) {
      return 'Property Type does not match the selected Property Category'
    }
  }

  if (doc.listing_type === 'Rent' && !doc.rent_type) {
    return 'Rent Type is mandatory for rental properties'
  }

  if (doc.price === undefined || doc.price === null || doc.price === '') {
    return 'Price is mandatory'
  }

  if (Number(doc.price) < 0) {
    return 'Price must be greater than or equal to zero'
  }

  if (!doc.currency) {
    return 'Currency is mandatory'
  }

  if (doc.bedrooms !== undefined && doc.bedrooms !== null && doc.bedrooms !== '') {
    if (Number(doc.bedrooms) < 0) {
      return 'Bedrooms must be greater than or equal to zero'
    }
  }

  if (doc.bathrooms !== undefined && doc.bathrooms !== null && doc.bathrooms !== '') {
    if (Number(doc.bathrooms) < 0) {
      return 'Bathrooms must be greater than or equal to zero'
    }
  }

  if (doc.area_sqft !== undefined && doc.area_sqft !== null && doc.area_sqft !== '') {
    if (Number(doc.area_sqft) < 0) {
      return 'Area must be greater than or equal to zero'
    }
  }

  if (doc.is_featured) {
    if (!doc.featured_from) return 'Featured From is mandatory'
    if (!doc.featured_until) return 'Featured Until is mandatory'
  }

  return null
}

export function getFieldErrors(doc) {
  const errors = {}

  if (!doc.title) {
    errors.title = 'Title is mandatory'
  } else {
    const titleLetters = doc.title.replace(/\s+/g, '').length
    if (titleLetters > 50) {
      errors.title = 'Title must not exceed 30 letters'
    }
  }

  // Mandatory fields from configs
  for (const fieldname in fieldConfigs.value) {
    const config = fieldConfigs.value[fieldname]
    const value = doc[fieldname]

    if (config.is_mandatory && (!value || value === '')) {
      errors[fieldname] = `${config.label || fieldname} is mandatory`
    }
  }

  if (doc.listing_type === 'Rent' && !doc.rent_type) {
    errors.rent_type = 'Rent Type is mandatory for rental properties'
  }

  if (doc.price === undefined || doc.price === null || doc.price === '') {
    errors.price = 'Price is mandatory'
  } else if (Number(doc.price) < 0) {
    errors.price = 'Price must be greater than or equal to zero'
  }

  if (!doc.currency) {
    errors.currency = 'Currency is mandatory'
  }

  if (doc.is_featured) {
    if (!doc.featured_from) errors.featured_from = 'Featured From is mandatory'
    if (!doc.featured_until) errors.featured_until = 'Featured Until is mandatory'
  }

  return errors
}

export function normalizePropertyDoc(doc) {
  if (!doc) return

  if (doc.listing_type === 'Buy' && doc.rent_type) {
    doc.rent_type = ''
  }

  if (!doc.is_featured) {
    doc.featured_from = ''
    doc.featured_until = ''
  }

  if (
    doc.property_category &&
    doc.property_type &&
    !getPropertyTypeOptions(doc.property_category).includes(doc.property_type)
  ) {
    doc.property_type = ''
  }

  return doc
}
