import { sessionStore } from '@/stores/session'
import { agentStore } from '@/stores/agent'

const PROPERTY_FIELD_GROUPS = {
  sidebar: [
    {
      name: 'overview',
      label: 'Overview',
      opened: true,
      fields: [
        'title',
        'property_code',
        'status',
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
      fields: ['is_featured', 'featured_until', 'is_sold', 'is_rented', 'views_count'],
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
            ['title', 'developer', 'agent', 'status', 'is_sold', 'is_rented'],
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
            ['trakheesi_permit_number', 'trakheesi_qr_code', 'zone_name'],
            ['payment_plan_table', 'project_units_table'],
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
          columns: [['primary_image', 'gallery'], ['is_featured', 'featured_until', 'views_count']],
        },
      ],
    },
  ],
  quickEntry: [
    {
      name: 'basics_tab',
      label: 'Basics',
      sections: [
        {
          name: 'basics_section',
          label: 'Basic Information',
          columns: [
            ['title', 'agent', 'developer', 'status', 'property_category'],
            ['listing_type', 'property_type', 'completion_status', 'rent_type', 'property_code'],
          ],
        },
        {
          name: 'pricing_section',
          label: 'Pricing & Specs',
          columns: [['price', 'currency', 'bedrooms', 'bathrooms'], ['furnishing_status', 'area_sqft']],
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
          columns: [['area', 'city', 'state'], ['country', 'pincode']],
        },
        {
          name: 'content_section',
          label: 'Content',
          columns: [['description']],
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

              // C-04: Per-form override — show only agent full_name in search results
              if (fieldname === 'agent') {
                overrides.search_fields = 'full_name'
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

  return PROPERTY_FIELD_GROUPS.data.map((tab) => ({
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
            if (fieldname !== 'property_type') {
              return fieldname
            }

            fieldMap.property_type = getField(fieldMap, 'property_type', {
              options: getPropertyTypeOptions(doc.property_category),
            })
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

  return PROPERTY_FIELD_GROUPS.quickEntry.map((tab) => ({
    name: tab.name,
    label: tab.label,
    sections: buildSections(fieldMap, tab.sections),
  }))
}

export function validatePropertyDoc(doc) {
  if (!doc.title) {
    return 'Title is mandatory'
  }

  // C-13: Enforce title length between 10 and 200 characters
  const titleLen = doc.title.trim().length
  if (titleLen < 10) {
    return 'Title must be at least 10 characters'
  }
  if (titleLen > 200) {
    return 'Title must not exceed 200 characters'
  }

  // C-07: Trakheesi fields mandatory — admin (session.user === 'Administrator') can bypass
  const session = sessionStore()
  const isAdmin = session.user === 'Administrator'
  const { agentResource } = agentStore()
  const isAgent = !!(agentResource.data && agentResource.data.name)

  if (!isAdmin) {
    if (!doc.trakheesi_permit_number) {
      return 'Trakheesi Permit Number is mandatory'
    }

    if (!doc.trakheesi_qr_code) {
      return 'Trakheesi QR Code is mandatory'
    }
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

  return null
}

export function normalizePropertyDoc(doc) {
  if (!doc) return

  if (doc.listing_type === 'Buy') {
    doc.rent_type = ''
  }

  if (!doc.is_featured) {
    doc.featured_until = ''
  }

  if (
    doc.property_category &&
    doc.property_type &&
    !getPropertyTypeOptions(doc.property_category).includes(doc.property_type)
  ) {
    doc.property_type = ''
  }
}
