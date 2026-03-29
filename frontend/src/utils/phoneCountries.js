/** Default dial code (UAE) when the number has no international prefix. */
export const DEFAULT_PHONE_DIAL = '+971'

/**
 * Common countries for CRM onboarding (MENA-first, then global).
 * Dial codes must be unique for reliable parsing.
 */
export const PHONE_COUNTRIES = [
  { dial: '+971', label: 'UAE +971' },
  { dial: '+966', label: 'Saudi +966' },
  { dial: '+973', label: 'Bahrain +973' },
  { dial: '+974', label: 'Qatar +974' },
  { dial: '+965', label: 'Kuwait +965' },
  { dial: '+968', label: 'Oman +968' },
  { dial: '+962', label: 'Jordan +962' },
  { dial: '+961', label: 'Lebanon +961' },
  { dial: '+963', label: 'Syria +963' },
  { dial: '+964', label: 'Iraq +964' },
  { dial: '+967', label: 'Yemen +967' },
  { dial: '+20', label: 'Egypt +20' },
  { dial: '+212', label: 'Morocco +212' },
  { dial: '+213', label: 'Algeria +213' },
  { dial: '+216', label: 'Tunisia +216' },
  { dial: '+218', label: 'Libya +218' },
  { dial: '+249', label: 'Sudan +249' },
  { dial: '+27', label: 'South Africa +27' },
  { dial: '+234', label: 'Nigeria +234' },
  { dial: '+254', label: 'Kenya +254' },
  { dial: '+91', label: 'India +91' },
  { dial: '+92', label: 'Pakistan +92' },
  { dial: '+880', label: 'Bangladesh +880' },
  { dial: '+94', label: 'Sri Lanka +94' },
  { dial: '+977', label: 'Nepal +977' },
  { dial: '+44', label: 'UK +44' },
  { dial: '+353', label: 'Ireland +353' },
  { dial: '+33', label: 'France +33' },
  { dial: '+49', label: 'Germany +49' },
  { dial: '+39', label: 'Italy +39' },
  { dial: '+34', label: 'Spain +34' },
  { dial: '+31', label: 'Netherlands +31' },
  { dial: '+32', label: 'Belgium +32' },
  { dial: '+41', label: 'Switzerland +41' },
  { dial: '+43', label: 'Austria +43' },
  { dial: '+46', label: 'Sweden +46' },
  { dial: '+47', label: 'Norway +47' },
  { dial: '+45', label: 'Denmark +45' },
  { dial: '+358', label: 'Finland +358' },
  { dial: '+48', label: 'Poland +48' },
  { dial: '+420', label: 'Czech +420' },
  { dial: '+36', label: 'Hungary +36' },
  { dial: '+90', label: 'Turkey +90' },
  { dial: '+7', label: 'RU/KZ +7' },
  { dial: '+380', label: 'Ukraine +380' },
  { dial: '+86', label: 'China +86' },
  { dial: '+852', label: 'Hong Kong +852' },
  { dial: '+65', label: 'Singapore +65' },
  { dial: '+60', label: 'Malaysia +60' },
  { dial: '+66', label: 'Thailand +66' },
  { dial: '+63', label: 'Philippines +63' },
  { dial: '+62', label: 'Indonesia +62' },
  { dial: '+84', label: 'Vietnam +84' },
  { dial: '+81', label: 'Japan +81' },
  { dial: '+82', label: 'South Korea +82' },
  { dial: '+61', label: 'Australia +61' },
  { dial: '+64', label: 'New Zealand +64' },
  { dial: '+1', label: 'US/CA +1' },
  { dial: '+52', label: 'Mexico +52' },
  { dial: '+55', label: 'Brazil +55' },
  { dial: '+54', label: 'Argentina +54' },
]

let _sortedByDialLength = null

export function dialCodesLongestFirst() {
  if (!_sortedByDialLength) {
    _sortedByDialLength = [...PHONE_COUNTRIES].sort(
      (a, b) => b.dial.length - a.dial.length
    )
  }
  return _sortedByDialLength
}

/**
 * Split a stored phone string into dial code and national digits.
 */
export function parseInternationalPhone(raw) {
  if (raw == null || raw === '') {
    return { dial: DEFAULT_PHONE_DIAL, national: '' }
  }
  let s = String(raw).trim().replace(/[\s\-().]/g, '')
  if (s.startsWith('00')) {
    s = `+${s.slice(2)}`
  }
  if (!s.startsWith('+')) {
    const digits = s.replace(/\D/g, '')
    if (digits.length >= 10) {
      return parseInternationalPhone(`+${digits}`)
    }
    return { dial: DEFAULT_PHONE_DIAL, national: digits.replace(/^0+/, '') }
  }
  for (const { dial } of dialCodesLongestFirst()) {
    if (s.startsWith(dial)) {
      const national = s.slice(dial.length).replace(/\D/g, '')
      return { dial, national }
    }
  }
  const fallback = s.slice(1).replace(/\D/g, '')
  return { dial: DEFAULT_PHONE_DIAL, national: fallback }
}

export function formatInternationalPhone(dial, nationalDigits) {
  const n = String(nationalDigits || '').replace(/\D/g, '')
  if (!n) return ''
  const d = dial || DEFAULT_PHONE_DIAL
  return `${d}${n}`
}
