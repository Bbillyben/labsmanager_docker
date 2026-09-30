import { apiRequest } from './client'
import type { CalendarEvent, CalendarFilter, CalendarFilterValue, EmployeeLeave, LeaveCapabilities, LeaveWrite } from './employees'

export type ProjectCalendarParticipant = { id: number; title: string; capabilities: LeaveCapabilities }
const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/calendar/`

export function getProjectCalendar(projectId: string, range: { from: string; to: string }, filters: Record<string, CalendarFilterValue>, signal: AbortSignal) {
  const query = new URLSearchParams(range)
  for (const [key, value] of Object.entries(filters)) {
    const serialized = Array.isArray(value) ? value.join(',') : String(value)
    if (serialized) query.set(key, serialized)
  }
  return apiRequest<CalendarEvent[]>(`${base(projectId)}?${query}`, { signal })
}
export function getProjectCalendarFilters(projectId: string, signal: AbortSignal) {
  return apiRequest<CalendarFilter[]>(`${base(projectId)}filters/`, { signal })
}
export function getProjectCalendarParticipants(projectId: string, signal: AbortSignal) {
  return apiRequest<ProjectCalendarParticipant[]>(`${base(projectId)}participants/`, { signal })
}
export function createProjectCalendarLeave(projectId: string, employeeId: string, value: LeaveWrite) {
  return apiRequest<EmployeeLeave>(`${base(projectId)}leaves/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...value, employee_id: Number(employeeId) }) })
}
export function updateProjectCalendarLeave(projectId: string, leaveId: number, value: LeaveWrite) {
  return apiRequest<EmployeeLeave>(`${base(projectId)}leaves/${leaveId}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
}
export function deleteProjectCalendarLeave(projectId: string, leaveId: number) {
  return apiRequest<void>(`${base(projectId)}leaves/${leaveId}/`, { method: 'DELETE' })
}
