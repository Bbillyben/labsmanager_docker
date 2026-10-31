import { apiRequest } from './client'

/** Detail entities whose contribution lists are filtered by backend view permissions. */
export type UIEntity = 'project' | 'employee' | 'team'
/** Calendar view contributed by a plugin through the generic UI contract. */
export type UICalendarType = 'main' | 'project_all' | 'project' | 'employee' | 'team'
/** Plugin page navigation entry advertised by the backend. */
export type UIPageNavigation = { location: 'calendars'; labels: Partial<Record<'fr' | 'en', string>>; icon: string | null; order: number }
/** Scope encoded in the contribution endpoint; IDs are local to their owner. */
export type UIContributionScope =
  | { entity: UIEntity; objectId: number }
  | { calendarType: UICalendarType; objectId: number }
  | { providerSlug: string; calendarId: string }
  | { pluginKey: string }
/** Validated, server-visible declaration of an action, section, page, or tab. */
export type UIContribution = {
  /** Globally unique `plugin:<slug>:<local id>` identity. */
  id: string; plugin_slug: string; slot: string; type: 'action' | 'section' | 'page' | 'tab'
  label: string; icon: string | null; behavior: 'copy_url' | 'open_url' | 'action' | 'module' | null
  confirm: boolean; priority: number
  local_id?: string
  module?: string | null; component?: string | null; api_version?: number | null
  navigation?: UIPageNavigation | null
}
/** Module entry and context resolved by the backend after visibility checks. */
export type UIModuleDescriptor = UIContribution & {
  module_url: string; css_urls: string[]; asset_version: string
  context: { entity?: UIEntity; objectId?: number; pluginKey?: string; calendarType?: UICalendarType
    providerSlug?: string; calendarId?: string; name?: string; options?: string[]; actionUrl?: string }
}
/** Bounded structured content returned by a server-side section handler. */
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
/** Fetch the visible declarations for an authorized detail, calendar, or plugin page. */
export const getUIContributions = (scope: UIContributionScope, signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>(base(scope), { signal })
export const getUISection = (scope: UIContributionScope, id: string, signal: AbortSignal) => apiRequest<UISection>(detail(scope, id), { signal })
/** Execute a server action; the response may contain a one-time URL. */
export const runUIAction = (scope: UIContributionScope, id: string) => apiRequest<{ url?: string; message?: string }>(detail(scope, id), { method: 'POST' })
/** Resolve the validated assets and context for a plugin-provided action UI. */
export const getUIActionModule = (scope: UIContributionScope, id: string) => apiRequest<UIModuleDescriptor>(detail(scope, id))
export const getUIPages = (signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>('/api/v1/ui-contributions/pages/', { signal })
export const getUIPage = (pluginSlug: string, pageId: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(`/api/v1/ui-contributions/pages/${encodeURIComponent(pluginSlug)}/${encodeURIComponent(pageId)}/`, { signal })
const settingsPanelsBase = (pluginKey: string) => `/api/v1/ui-contributions/user-plugin/${encodeURIComponent(pluginKey)}/panels/`
export const getUISettingsPanels = (pluginKey: string, signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>(settingsPanelsBase(pluginKey), { signal })
export const getUISettingsPanel = (pluginKey: string, panelId: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(`${settingsPanelsBase(pluginKey)}${encodeURIComponent(panelId)}/`, { signal })
export const getUITab = (entity: UIEntity, objectId: number, id: string, signal: AbortSignal) => apiRequest<UIModuleDescriptor>(detail({ entity, objectId }, id), { signal })
