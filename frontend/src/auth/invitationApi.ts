import { apiRequest } from '../api/client'

export type InvitationSignup = {
  state: 'valid'
  email: string
  fields: { username: boolean; password2: boolean }
  password_hints: string[]
}

export function exchangeInvitation(token: string) {
  return apiRequest<InvitationSignup>('/api/v1/auth/invitations/bridge/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }),
  })
}

export function getInvitationSignup() {
  return apiRequest<InvitationSignup>('/api/v1/auth/invitations/current/')
}

export function completeInvitationSignup(fields: { username: string; password1: string; password2: string }) {
  return apiRequest<{ state: 'complete'; authenticated: boolean; redirect_url: string | null }>('/api/v1/auth/invitations/current/', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields),
  })
}
