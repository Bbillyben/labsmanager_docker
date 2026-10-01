import { apiRequest } from './client'

export type PreferenceType = 'project' | 'employee' | 'team'
export type PreferenceStatus = { favorite: boolean; subscription: boolean }
export type FavoriteItem = { type: string; group: 'projects' | 'employees' | 'teams' | 'institutions'; id: number; label: string; url: string; legacy: boolean }
export const favoritesChangedEvent = 'labsmanager:favorites-changed'

const objectUrl = (type: PreferenceType, id: string | number) => `/api/v1/preferences/${type}/${encodeURIComponent(id)}/`
export const getObjectPreferences = (type: PreferenceType, id: string | number, signal: AbortSignal) => apiRequest<PreferenceStatus>(objectUrl(type, id), { signal })
export async function setObjectPreference(type: PreferenceType, id: string | number, value: Partial<PreferenceStatus>) {
  const saved = await apiRequest<PreferenceStatus>(objectUrl(type, id), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
  if ('favorite' in value) window.dispatchEvent(new Event(favoritesChangedEvent))
  return saved
}
export const getFavorites = (signal: AbortSignal) => apiRequest<FavoriteItem[]>('/api/v1/favorites/', { signal })
