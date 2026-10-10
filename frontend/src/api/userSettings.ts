import { apiRequest } from './client'
import type { SettingData, SettingValue } from './settings'

export type UserSettingSection = 'interface' | 'notifications' | 'stale'
export type UserSettingData = SettingData & { can_change: boolean; units?: string }
export type UserAccount = {
  username: string; first_name: string; last_name: string; last_login: string | null
  employee: { id: number; name: string } | null; has_usable_password: boolean
  can_add: boolean; emails: EmailAddress[]
}
export type EmailAddress = {
  id: number; email: string; verified: boolean; primary: boolean
  can_delete: boolean; can_make_primary: boolean; can_resend: boolean
}
export type EmailCollection = Pick<UserAccount, 'can_add' | 'emails'>

const base = '/api/v1/settings/'
export const getUserSettings = (section: UserSettingSection, signal: AbortSignal) => apiRequest<{ settings: UserSettingData[] }>(`${base}user/${section}/`, { signal })
export const updateUserSetting = (section: UserSettingSection, key: string, value: SettingValue) => apiRequest<UserSettingData>(`${base}user/${section}/${encodeURIComponent(key)}/`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }),
})
export const sendTestNotification = () => apiRequest<{ sent: boolean }>(`${base}notifications/test-email/send/`, { method: 'POST' })
export const previewTestNotification = () => apiRequest<string>(`${base}notifications/test-email/preview/`, { method: 'POST' }, 'text')
export const getUserAccount = (signal: AbortSignal) => apiRequest<UserAccount>(`${base}account/`, { signal })
export const changeUserPassword = (values: { oldpassword?: string; password1: string; password2: string }) => apiRequest<{ saved: boolean; logged_out: boolean }>(`${base}account/password/`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
})
export const addUserEmail = (email: string) => apiRequest<EmailCollection>(`${base}account/emails/`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }),
})
export const updateUserEmail = (id: number, action: 'primary' | 'resend') => apiRequest<EmailCollection>(`${base}account/emails/${id}/`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
})
export const removeUserEmail = (id: number) => apiRequest<EmailCollection>(`${base}account/emails/${id}/`, { method: 'DELETE' })
