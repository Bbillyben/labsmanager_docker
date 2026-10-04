import { apiRequest } from './client'

export type MutableField = {
  key: string; label: string; type: 'text' | 'boolean' | 'choice' | 'relation' | 'color'
  required: boolean; readonly: boolean; default?: string | number | boolean | null; choices: { value: string | number; label: string }[]
}
export type MutableCapabilities = { can_view: boolean; can_add: boolean; can_change: boolean; can_delete: boolean }
export type MutableList = {
  key: string; group: string; label: string; columns: string[]; fields: MutableField[]
  capabilities: MutableCapabilities; renderers?: Record<string, 'tree'>
}
export type MutableRow = { id: number; values: Record<string, string | number | boolean | null>; capabilities: MutableCapabilities; editable_fields: string[]; tree_level?: number }
export type MutableGroup = { key: string; label: string; lists: MutableList[] }

const base = '/api/v1/settings/lists/'
export const getMutableLists = (signal: AbortSignal) => apiRequest<{ groups: MutableGroup[] }>(base, { signal })
export const getMutableList = (key: string, signal: AbortSignal) => apiRequest<{ list: MutableList; rows: MutableRow[] }>(`${base}${encodeURIComponent(key)}/`, { signal })
export const createMutableItem = (key: string, values: Record<string, unknown>) => apiRequest<MutableRow>(`${base}${encodeURIComponent(key)}/`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
})
export const updateMutableItem = (key: string, id: number, values: Record<string, unknown>) => apiRequest<MutableRow>(`${base}${encodeURIComponent(key)}/${id}/`, {
  method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
})
export const deleteMutableItem = (key: string, id: number) => apiRequest<void>(`${base}${encodeURIComponent(key)}/${id}/`, { method: 'DELETE' })
