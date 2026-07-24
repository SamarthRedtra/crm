/** Agent onboarding is complete once ops/KYC has set status to Verified. */
export function isAgentOnboardingComplete(agent) {
  return agent?.status === 'Verified'
}

/** True when the user has an Agent record that still needs onboarding. */
export function isUnverifiedAgent(agent) {
  return Boolean(agent?.name) && !isAgentOnboardingComplete(agent)
}

export function agentNeedsDdaLicenseSync(agent) {
  if (!agent?.name || !isAgentOnboardingComplete(agent)) return false
  return Boolean(
    agent.requires_agent_license_verification || agent.requires_license_verification,
  )
}
