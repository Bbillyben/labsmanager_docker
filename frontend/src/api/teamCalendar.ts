import { apiRequest } from './client'
import type { CalendarEvent, CalendarFilter, CalendarFilterValue, EmployeeLeave, LeaveWrite } from './employees'
import type { ProjectCalendarParticipant } from './projectCalendar'

const base = (teamId: string) => `/api/v1/teams/${encodeURIComponent(teamId)}/calendar/`

export function getTeamCalendar(teamId: string, range: { from: string; to: string }, filters: Record<string, CalendarFilterValue>, signal: AbortSignal) {
  const query = new URLSearchParams(range)
  for (const [key, value] of Object.entries(filters)) {
    const serialized = Array.isArray(value) ? value.join(',') : String(value)
    if (serialized) query.set(key, serialized)
  }
  return apiRequest<CalendarEvent[]>(`${base(teamId)}?${query}`, { signal })
}
export const getTeamCalendarFilters = (teamId: string, signal: AbortSignal) => apiRequest<CalendarFilter[]>(`${base(teamId)}filters/`, { signal })
export const getTeamCalendarParticipants = (teamId: string, signal: AbortSignal) => apiRequest<ProjectCalendarParticipant[]>(`${base(teamId)}participants/`, { signal })
export const createTeamCalendarLeave = (teamId: string, employeeId: string, value: LeaveWrite) => apiRequest<EmployeeLeave>(`${base(teamId)}leaves/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...value, employee_id: Number(employeeId) }) })
export const updateTeamCalendarLeave = (teamId: string, leaveId: number, value: LeaveWrite) => apiRequest<EmployeeLeave>(`${base(teamId)}leaves/${leaveId}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
export const deleteTeamCalendarLeave = (teamId: string, leaveId: number) => apiRequest<void>(`${base(teamId)}leaves/${leaveId}/`, { method: 'DELETE' })
