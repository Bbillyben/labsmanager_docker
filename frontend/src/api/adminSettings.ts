import { apiRequest } from './client'
import type { UserSettingData } from './userSettings'
import type { SettingValue } from './settings'

const base = '/api/v1/settings/admin/'
const json = { 'Content-Type': 'application/json' }
export type AdminUser = { id: number; username: string; name: string; last_login: string | null; is_active: boolean; is_staff: boolean; employee: { id: number; name: string } | null }
export type AdminInvitation = { id: number; email: string; created: string; sent: string | null; accepted: boolean; key_expired: boolean; inviter: { id: number; username: string } | null }
export type PendingNotification = { id: number; user: string; source_type: string; action: string; object: string; created: string }
export type PluginError = { stage: string; name: string; message: string }
export type PluginSummary = { key: string; human_name: string; description: string; author: string; pub_date: string | null; version: string | null; website: string | null; license: string | null; mixins: string[] }
export type PluginDetail = PluginSummary & { sections: { settings?: UserSettingData[]; schedule?: { name: string; function: string; schedule_type: string; repeat: number | null; next_run: string | null; success: boolean }[]; urls?: { base_url: string; routes: { name: string; url: string; href: string | null }[] } } }

export const getAdminSettings = (section: 'general' | 'plugins', signal: AbortSignal) => apiRequest<{ settings: UserSettingData[] }>(`${base}${section}/settings/`, { signal })
export const updateAdminSetting = (section: 'general' | 'plugins', key: string, value: SettingValue) => apiRequest<UserSettingData>(`${base}${section}/settings/${encodeURIComponent(key)}/`, { method: 'PATCH', headers: json, body: JSON.stringify({ value }) })
export const getAdminUsers = (signal: AbortSignal) => apiRequest<{ results: AdminUser[] }>(`${base}users/`, { signal })
export const getEmployeeOptions = (signal: AbortSignal) => apiRequest<{ results: { id: number; name: string }[] }>(`${base}users/employee-options/`, { signal })
export const updateAdminUserEmployee = (id: number, employeeId: number | null) => apiRequest<AdminUser>(`${base}users/${id}/employee/`, { method: 'PATCH', headers: json, body: JSON.stringify({ employee_id: employeeId }) })
export const getAdminInvitations = (signal: AbortSignal) => apiRequest<{ results: AdminInvitation[] }>(`${base}invitations/`, { signal })
export const sendAdminInvitation = (email: string) => apiRequest<AdminInvitation>(`${base}invitations/`, { method: 'POST', headers: json, body: JSON.stringify({ email }) })
export const removeExpiredAdminInvitations = () => apiRequest<{ deleted: number }>(`${base}invitations/remove-expired/`, { method: 'POST' })
export const getAdminNotifications = (signal: AbortSignal) => apiRequest<{ results: PendingNotification[] }>(`${base}notifications/`, { signal })
export const runAdminNotificationAction = (action: 'check' | 'send') => apiRequest<{ counts?: Record<string, number>; sent?: number; results: PendingNotification[] }>(`${base}notifications/${action}/`, { method: 'POST' })
export const getAdminPlugins = (signal: AbortSignal) => apiRequest<{ results: PluginSummary[]; errors: PluginError[] }>(`${base}plugins/`, { signal })
export const reloadAdminPlugins = () => apiRequest<{ results: PluginSummary[]; errors: PluginError[] }>(`${base}plugins/reload/`, { method: 'POST' })
export const getAdminPlugin = (key: string, signal: AbortSignal) => apiRequest<PluginDetail>(`${base}plugins/${encodeURIComponent(key)}/`, { signal })
export const updateAdminPluginSetting = (plugin: string, key: string, value: SettingValue) => apiRequest<UserSettingData>(`${base}plugins/${encodeURIComponent(plugin)}/settings/${encodeURIComponent(key)}/`, { method: 'PATCH', headers: json, body: JSON.stringify({ value }) })
