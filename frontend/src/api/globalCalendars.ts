import { apiRequest } from './client'
import type { CalendarEvent, CalendarFilter, CalendarFilterValue } from './employees'
import type { PlanningMilestone, PlanningMilestoneState } from './planning'

export type GlobalEmployeeCalendar = { events: CalendarEvent[]; employee_names: Record<string, string>; resources: Array<{ id: string; title: string }> }
export type GlobalProjectPlanning = {
  projects: Array<{ id: number; name: string; start_date: string | null; end_date: string | null }>
  items: PlanningMilestone[]
  events: CalendarEvent[]
  milestone_statuses: PlanningMilestoneState[]
}

export function globalCalendarQuery(range: { from: string; to: string }, filters: URLSearchParams, plugins: Record<string, CalendarFilterValue>) {
  const query = new URLSearchParams(range)
  for (const [key, value] of filters) if (value) query.set(key, value)
  for (const [key, value] of Object.entries(plugins)) {
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item))
    else query.set(key, String(value))
  }
  return query.toString()
}

export const getGlobalEmployeeCalendar = (query: string, signal: AbortSignal) => apiRequest<GlobalEmployeeCalendar>(`/api/v1/calendars/employees/?${query}`, { signal })
export const getGlobalProjectPlanning = (query: string, signal: AbortSignal) => apiRequest<GlobalProjectPlanning>(`/api/v1/calendars/projects/?${query}`, { signal })
export const getGlobalCalendarFilters = (scope: 'employees' | 'projects', signal: AbortSignal) => apiRequest<CalendarFilter[]>(`/api/v1/calendars/${scope}/filters/`, { signal })
