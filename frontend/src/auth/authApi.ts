import { apiRequest } from '../api/client'
import type { AuthenticationState, CurrentUser, LoginCredentials } from './types'

export function getCurrentUser(signal?: AbortSignal) {
  return apiRequest<CurrentUser>('/api/v1/me/', { signal })
}

export function login(credentials: LoginCredentials) {
  return apiRequest<AuthenticationState>('/api/v1/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  })
}

export function logout() {
  return apiRequest<AuthenticationState>('/api/v1/auth/logout/', { method: 'POST' })
}
