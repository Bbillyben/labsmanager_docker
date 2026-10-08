import { apiRequest } from './client'

export type DashboardSummary = { id: number; name: string; icon: string; is_default: boolean; position: number; scope: 'user' | 'project'; project_id?: number | null }
export type DashboardWidget = {
  id: string; definition_key: string; source_key: string; renderer_key: string; title: string; config: Record<string, string | number | boolean>
  x: number; y: number; width: number; height: number; logical_order: number
  available: boolean; data: unknown; error: boolean
}
export type DashboardKpiData = { value: string | number; label?: string; context?: string; secondary?: string; tone?: 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'muted'; centered_ratio?: number; budget_percent?: number; time_percent?: number; progress_percent?: number }
export type DashboardSeriesData = { series: { key: string; label: string; kind?: string; points: { date: string; value: number }[] }[]; meta?: { display?: string; group_by?: string; unit?: string } }
export type DashboardListItem = { key: string; label: string; secondary?: string; date?: string; status?: string; href?: string; icon?: string; tone?: string; severity?: 'info' | 'warning' | 'danger'; current?: number; total?: number; percent?: number }
export type DashboardListData = { items: DashboardListItem[] }
export type DashboardOverviewData = {
  summary: { amount: number; spent: number; percent: number | null; count: number; count_label: string; attention_count: number }
  items: { key: string; label: string; secondary?: string | null; href?: string; date?: string | null; current: number; total: number; percent: number | null; remaining_days: number | null; status: 'normal' | 'ending_soon' | 'expired' }[]
}
export type DashboardDeadlineData = {
  summary: { count: number; overdue_count: number; due_soon_count: number }
  items: { key: string; label: string; project_name: string; date: string | null; href: string;
    days_until: number | null; state: 'overdue' | 'today' | 'due_soon' | 'upcoming' | 'completed' | 'unscheduled' }[]
}
export type DashboardContractData = {
  summary: { count: number; ending_soon_count: number; stale_count: number }
  items: { key: string; employee_name: string; employee_href: string | null; contract_type: string;
    project_name: string; project_href: string | null; date: string | null; days_until: number | null;
    state: 'stale' | 'ending_soon' | 'current' | 'ended' | 'no_date' }[]
}
export type DashboardEmployeeMovementsData = {
  summary: { count: number; arrivals_count: number; departures_count: number }
  items: { key: string; name: string; href: string; role: string | null; team_name: string | null; team_href: string | null;
    state: 'arriving' | 'leaving' | 'arrived_recently' | 'departed' | 'active' | 'inactive';
    date: string | null; days_until: number | null }[]
}
export type DashboardTaskWorkloadData = {
  summary: { count: number; overdue_count: number; due_soon_count: number }
  items: { key: string; title: string; href: string; project_name: string; project_href: string;
    assignees: { id: number; name: string; href: string | null }[]; date: string | null; days_until: number | null;
    state: 'overdue' | 'today' | 'due_soon' | 'later' | 'done' | 'unscheduled' }[]
}
export type DashboardProjectPortfolioData = {
  summary: { count: number; active_count: number; ending_soon_count: number; attention_count: number }
  items: { key: string; name: string; href: string; start_date: string | null; end_date: string | null;
    temporal_percent: number | null; temporal_state: 'upcoming' | 'active' | 'ending_soon' | 'ended' | 'unknown';
    financial: { amount: number; spent: number; percent: number } | null;
    next_milestone: { title: string; date: string; days_until: number; href: string } | null;
    overdue_task_count: number; attention_signals: string[] }[]
}
export type DashboardEmployeeWorkloadData =
  | { mode: 'single'; employee: { id: number; name: string; href: string };
      metrics: { key: string; value: number; unit: 'percent' | 'count'; reference_value: number | null }[] }
  | { mode: 'comparison'; metric: string; unit: 'percent' | 'count'; reference_value: number | null;
      items: { employee_id: number; employee_name: string; value: number; href: string }[] }
export type DashboardTimelineData = {
  window_start: string; today: string; window_end: string; earlier_overdue_count: number
  events: { id: string; source_type: string; source_label: string; date: string; title: string;
    project_name?: string; project_href?: string; secondary?: string | null; href?: string;
    state: 'done' | 'overdue' | 'today' | 'soon' | 'future'; tone: string; icon?: string }[]
}
export type DashboardDetail = DashboardSummary & { widgets: DashboardWidget[] }
export type WidgetDefinition = {
  key: string; title: string; category: string; renderer_key: string; source_key: string
  supported_scopes: string[]; default_size: [number, number]; min_size: [number, number]; max_size: [number, number]
  allow_multiple: boolean; printable: boolean; icon: string; config_fields: Record<string, string>
}
export type ConfigField = { type: 'string' | 'boolean' | 'integer' | 'choice' | 'project' | 'employee' | 'team'; label?: string; group?: string; required?: boolean; default?: string | number | boolean; min?: number; max?: number; max_length?: number; choices?: (string | number)[] }
export type DashboardSource = { key: string; label: string; description: string; category: string; compatible_renderers: string[]; default_renderer: string; allow_multiple: boolean; config_fields: Record<string, ConfigField | string> }
export type DashboardCatalog = { scope: string; definitions: WidgetDefinition[]; sources: DashboardSource[]; renderers: Record<string, { label: string; config_fields: Record<string, ConfigField | string> }>; project_options?: { id: number; name: string }[]; employee_options?: { id: number; name: string }[]; team_options?: { id: number; name: string }[] }
const base = '/api/v1/dashboards/'
const dashboardUrl = (id: number) => `${base}${id}/`
const json = (value: unknown) => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })

export const listDashboards = () => apiRequest<DashboardSummary[]>(base)
export const getDashboard = (id: number) => apiRequest<DashboardDetail>(dashboardUrl(id))
export const getDashboardCatalog = (projectId?: string | number) => apiRequest<DashboardCatalog>(projectId ? `/api/v1/projects/${projectId}/dashboard/catalog/` : `${base}catalog/`)
export const getProjectDashboard = (projectId: string | number) => apiRequest<DashboardDetail>(`/api/v1/projects/${projectId}/dashboard/`)
export const createDashboard = (name: string, template: string) => apiRequest<DashboardSummary>(base, { method: 'POST', ...json({ name, template }) })
export const renameDashboard = (id: number, name: string) => apiRequest<DashboardSummary>(dashboardUrl(id), { method: 'PATCH', ...json({ name }) })
export const deleteDashboard = (id: number) => apiRequest<void>(dashboardUrl(id), { method: 'DELETE' })
export const duplicateDashboard = (id: number) => apiRequest<DashboardSummary>(`${dashboardUrl(id)}duplicate/`, { method: 'POST' })
export const setDefaultDashboard = (id: number) => apiRequest<DashboardSummary>(`${dashboardUrl(id)}default/`, { method: 'POST' })
export const reorderDashboards = (ids: number[]) => apiRequest<DashboardSummary[]>(`${base}reorder/`, { method: 'PATCH', ...json({ ids }) })
export const addDashboardWidget = (id: number, sourceKey: string, rendererKey: string, title: string, config: DashboardWidget['config']) => apiRequest<DashboardWidget>(`${dashboardUrl(id)}widgets/`, { method: 'POST', ...json({ source_key: sourceKey, renderer_key: rendererKey, title, config }) })
export const updateDashboardWidget = (id: number, widgetId: string, title: string, config: DashboardWidget['config'], rendererKey: string) => apiRequest<DashboardWidget>(`${dashboardUrl(id)}widgets/${widgetId}/`, { method: 'PATCH', ...json({ title, config, renderer_key: rendererKey }) })
export const deleteDashboardWidget = (id: number, widgetId: string) => apiRequest<void>(`${dashboardUrl(id)}widgets/${widgetId}/`, { method: 'DELETE' })
export type LayoutUpdate = Pick<DashboardWidget, 'id' | 'x' | 'y' | 'width' | 'height' | 'logical_order'>
export const saveDashboardLayout = (id: number, widgets: LayoutUpdate[]) => apiRequest(`${dashboardUrl(id)}layout/`, { method: 'PATCH', ...json({ widgets }) })
