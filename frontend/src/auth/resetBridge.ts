import { apiRequest } from '../api/client';

export function passwordResetBridgeUrl(key: string) {
  return `/api/v1/auth/password/reset/bridge/${encodeURIComponent(key)}/`;
}

/** Exchange the reset link token for the password-reset flow. */
export function exchangePasswordResetToken(key: string) {
  return apiRequest<{ valid: true; uid: string }>(passwordResetBridgeUrl(key));
}
