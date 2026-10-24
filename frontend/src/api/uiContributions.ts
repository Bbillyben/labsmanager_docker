import { apiRequest } from './client'

export type UIEntity = 'project' | 'employee' | 'team'
export type UICalendarType = 'main' | 'project_all' | 'project' | 'employee' | 'team'
export type UIContributionScope =
  | { entity: UIEntity; objectId: number }
  | { calendarType: UICalendarType; objectId: number }
  | { pluginKey: string }
export type UIContribution = {
  id: string; plugin_slug: string; slot: string; type: 'action' | 'section'
  label: string; icon: string | null; behavior: 'copy_url' | 'open_url' | 'action' | null
  confirm: boolean; priority: number
}
export type UISection =
  | { format: 'text'; text: string }
  | { format: 'properties'; items: Array<{ label: string; value: string }> }
  | { format: 'items'; items: Array<{ label: string; description: string; url?: string }> }
  | { format: 'links'; items: Array<{ label: string; url: string }> }

const base = (scope: UIContributionScope) => {
  if ('entity' in scope) return `/api/v1/ui-contributions/${scope.entity}/${scope.objectId}/`
  if ('calendarType' in scope) return `/api/v1/ui-contributions/calendar/${scope.calendarType}/${scope.objectId}/`
  return `/api/v1/ui-contributions/user-plugin/${encodeURIComponent(scope.pluginKey)}/`
}
const detail = (scope: UIContributionScope, id: string) => `${base(scope)}${encodeURIComponent(id)}/`
export const getUIContributions = (scope: UIContributionScope, signal: AbortSignal) => apiRequest<{ contributions: UIContribution[] }>(base(scope), { signal })
export const getUISection = (scope: UIContributionScope, id: string, signal: AbortSignal) => apiRequest<UISection>(detail(scope, id), { signal })
export const runUIAction = (scope: UIContributionScope, id: string) => apiRequest<{ url?: string; message?: string }>(detail(scope, id), { method: 'POST' })
