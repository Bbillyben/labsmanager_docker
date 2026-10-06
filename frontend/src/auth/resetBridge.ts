import { apiRequest } from '../api/client'

export function passwordResetBridgeUrl(key: string) {
  return `/api/v1/auth/password/reset/bridge/${encodeURIComponent(key)}/`
}

export function exchangePasswordResetToken(key: string) {
  return apiRequest<{ valid: true; uid: string }>(passwordResetBridgeUrl(key))
}
