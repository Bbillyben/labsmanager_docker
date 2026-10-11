import { apiRequest } from '../api/client'

export type EmailConfirmation = {
  state: 'confirmation_required' | 'confirmed' | 'already_confirmed'
  email?: string
}

export function exchangeEmailConfirmationKey(key: string) {
  return apiRequest<EmailConfirmation>('/api/v1/auth/email/confirm/bridge/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }),
  })
}

export function getEmailConfirmation() {
  return apiRequest<EmailConfirmation>('/api/v1/auth/email/confirm/')
}

export function confirmEmail() {
  return apiRequest<EmailConfirmation>('/api/v1/auth/email/confirm/', { method: 'POST' })
}
