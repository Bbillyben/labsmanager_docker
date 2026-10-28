import { apiRequest } from './client'

export type UIEntity = 'project' | 'employee' | 'team'
export type UICalendarType = 'main' | 'project_all' | 'project' | 'employee' | 'team'
export type UIPageNavigation = { location: 'calendars'; labels: Partial<Record<'fr' | 'en', string>>; icon: string | null; order: number }
export type UIContributionScope =
  | { entity: UIEntity; objectId: number }
  | { calendarType: UICalendarType; objectId: number }
  | { providerSlug: string; calendarId: string }
  | { pluginKey: string }
export type UIContribution = {
  id: string; plugin_slug: string; slot: string; type: 'action' | 'section' | 'page' | 'tab'
  label: string; icon: string | null; behavior: 'copy_url' | 'open_url' | 'action' | 'module' | null
  confirm: boolean; priority: number
  local_id?: string
  module?: string | null; component?: string | null; api_version?: number | null
  navigation?: UIPageNavigation | null
}
export type UIModuleDescriptor = UIContribution & {
  module_url: string; css_urls: string[]; asset_version: string
  context: { entity?: UIEntity; objectId?: number; pluginKey?: string; calendarType?: UICalendarType
    providerSlug?: string; calendarId?: string; name?: string; options?: string[]; actionUrl?: string }
}
export type UISection =
  | { format: 'text'; text: string }
  | { format: 'properties'; items: Array<{ label: string; value: string }> }
  | { format: 'items'; items: Array<{ label: string; description: string; url?: string }> }
  | { format: 'links'; items: Array<{ label: string; url: string }> }

const base = (scope: UIContributionScope) => {
  if ('entity' in scope) return `/api/v1/ui-contributions/${scope.entity}/${scope.objectId}/`
  if ('calendarType' in scope) return `/api/v1/ui-contributions/calendar/${scope.calendarType}/${scope.objectId}/`
  if ('providerSlug' in scope) return `/api/v1/ui-contributions/published-calendar/${encodeURIComponent(scope.providerSlug)}/${encodeURIComponent(scope.calendarId)}/`
  return `/api/v1/ui-contributions/user-plugin/${encodeURIComponent(scope.pluginKey)}/`
}
const detail = (scope: UIContributionScope, id: string) => `${base(scope)}${encodeURIComponent(id)}/`
export const getUIContributions = (scope: UIContributionScope, signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>(base(scope), { signal })
export const getUISection = (scope: UIContributionScope, id: string, signal: AbortSignal) => apiRequest<UISection>(detail(scope, id), { signal })
export const runUIAction = (scope: UIContributionScope, id: string) => apiRequest<{ url?: string; message?: string }>(detail(scope, id), { method: 'POST' })
export const getUIActionModule = (scope: UIContributionScope, id: string) => apiRequest<UIModuleDescriptor>(detail(scope, id))
export const getUIPages = (signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>('/api/v1/ui-contributions/pages/', { signal })
export const getUIPage = (pluginSlug: string, pageId: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(`/api/v1/ui-contributions/pages/${encodeURIComponent(pluginSlug)}/${encodeURIComponent(pageId)}/`, { signal })
const settingsPanelsBase = (pluginKey: string) => `/api/v1/ui-contributions/user-plugin/${encodeURIComponent(pluginKey)}/panels/`
export const getUISettingsPanels = (pluginKey: string, signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>(settingsPanelsBase(pluginKey), { signal })
export const getUISettingsPanel = (pluginKey: string, panelId: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(`${settingsPanelsBase(pluginKey)}${encodeURIComponent(panelId)}/`, { signal })
export const getUITab = (entity: UIEntity, objectId: number, id: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(detail({ entity, objectId }, id), { signal })
