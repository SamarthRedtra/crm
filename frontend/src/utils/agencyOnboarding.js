/** Agency ops verification is complete once verification_status is Verified. */
export function isAgencyVerificationComplete(context) {
  return (context?.verification_status || 'Verified') === 'Verified'
}

/** Agency onboarding is complete once onboarding_status is Completed. */
export function isAgencyOnboardingComplete(context) {
  return (
    context?.onboarding_status === 'Completed' || Boolean(context?.onboarding_completed)
  )
}

/** Non-blocking DDA sync warning after ops verification is approved. */
export function agencyNeedsDdaLicenseSync(context) {
  if (!context?.agency || !isAgencyVerificationComplete(context)) return false
  return Boolean(context.requires_agency_license_verification)
}
