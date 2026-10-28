import { apiRequest } from './client'
import type { SettingValue } from './settings'
import type { UserSettingData } from './userSettings'

const json = { 'Content-Type': 'application/json' }
const pluginBase = (key: string) => `/api/v1/plugins/${encodeURIComponent(key)}/`

export type PersonalPlugin = { key: string; human_name: string; description: string; user_settings: boolean; user_tokens: boolean; ui_actions?: boolean; ui_panels?: boolean }
export type PluginTokenKind = 'plugin' | 'user'
export type TokenScope = { name: string; label: string; description: string }
export type PluginToken = {
  public_id: string; name: string; kind: PluginTokenKind; scopes: string[]
  created_at: string; expires_at: string | null; revoked_at: string | null; last_used_at: string | null
}
export type PluginTokenList = { scopes: TokenScope[]; tokens: PluginToken[] }
export type CreatedPluginToken = PluginToken & { token: string }

export const getPersonalPlugins = (signal: AbortSignal) => apiRequest<{ results: PersonalPlugin[] }>('/api/v1/plugins/mine/', { signal })
export const getPluginUserSettings = (key: string, signal: AbortSignal) => apiRequest<{ settings: UserSettingData[] }>(`${pluginBase(key)}user-settings/`, { signal })
export const updatePluginUserSetting = (plugin: string, key: string, value: SettingValue) => apiRequest<UserSettingData>(`${pluginBase(plugin)}user-settings/${encodeURIComponent(key)}/`, { method: 'PATCH', headers: json, body: JSON.stringify({ value }) })
export const resetPluginUserSetting = (plugin: string, key: string) => apiRequest<UserSettingData>(`${pluginBase(plugin)}user-settings/${encodeURIComponent(key)}/`, { method: 'DELETE' })

const tokenBase = (key: string, kind: PluginTokenKind) => `${pluginBase(key)}tokens/${kind}/`
export const getPluginTokens = (key: string, kind: PluginTokenKind, signal: AbortSignal) => apiRequest<PluginTokenList>(tokenBase(key, kind), { signal })
export const createPluginToken = (key: string, kind: PluginTokenKind, name: string, scopes: string[], expiresAt: string | null) => apiRequest<CreatedPluginToken>(tokenBase(key, kind), { method: 'POST', headers: json, body: JSON.stringify({ name, scopes, expires_at: expiresAt }) })
export const renamePluginToken = (key: string, kind: PluginTokenKind, publicId: string, name: string) => apiRequest<PluginToken>(`${tokenBase(key, kind)}${encodeURIComponent(publicId)}/`, { method: 'PATCH', headers: json, body: JSON.stringify({ name }) })
export const revokePluginToken = (key: string, kind: PluginTokenKind, publicId: string) => apiRequest<PluginToken>(`${tokenBase(key, kind)}${encodeURIComponent(publicId)}/`, { method: 'DELETE' })
