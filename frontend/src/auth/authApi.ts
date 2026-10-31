import { apiRequest } from '../api/client'
import type { AuthenticationState, CurrentUser, LoginCredentials } from './types'

/** Load the current session and its API capabilities. */
export function getCurrentUser(signal?: AbortSignal) {
  return apiRequest<CurrentUser>('/api/v1/me/', { signal })
}

/** Authenticate with credentials through the existing auth endpoint. */
export function login(credentials: LoginCredentials) {
  return apiRequest<AuthenticationState>('/api/v1/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  })
}

/** End the current authenticated session. */
export function logout() {
  return apiRequest<AuthenticationState>('/api/v1/auth/logout/', { method: 'POST' })
}

export function requestPasswordReset(email: string) {
  return apiRequest<{ sent: true }>('/api/v1/auth/password/reset/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }),
  })
}

export function getPasswordReset(uid: string) {
  return apiRequest<{ valid: true; password_hints: string[] }>(`/api/v1/auth/password/reset/${encodeURIComponent(uid)}/`)
}

export function confirmPasswordReset(uid: string, password1: string, password2: string) {
  return apiRequest<{ saved: true }>(`/api/v1/auth/password/reset/${encodeURIComponent(uid)}/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password1, password2 }),
  })
}
