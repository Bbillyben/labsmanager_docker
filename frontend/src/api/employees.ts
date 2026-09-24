import { apiRequest } from './client'
import { employeeFilters } from '../config/employeeFilters'
import { filterDefaultsMarker, readFilterQuery, withFilterDefaults } from '../filters/url'

export type EmployeeIdentity = { id: number; first_name: string; last_name: string }
export type EmployeeStatus = { id: number; code: string; name: string }
export type EmployeeListItem = EmployeeIdentity & {
  entry_date: string | null
  exit_date: string | null
  is_active: boolean
  current_statuses: EmployeeStatus[]
  superiors: EmployeeIdentity[]
}
export type EmployeeDetail = EmployeeListItem & {
  birth_date: string | null
  email: string | null
  contract_quotity: string | null
  project_quotity: string | null
  contribution_quotity: string | null
  active_milestones_count: number
}
export type EmployeeStatusHistoryItem = {
  id: number
  type: EmployeeStatus
  start_date: string | null
  end_date: string | null
  contractuality: { code: string; label: string }
  is_active: boolean
}
export type EmployeeHierarchyRelation = {
  id: number
  employee: EmployeeIdentity
  start_date: string | null
  end_date: string | null
  is_active: boolean
}
export type EmployeeHierarchy = {
  superiors: EmployeeHierarchyRelation[]
  subordinates: EmployeeHierarchyRelation[]
}
export type EmployeeGenericInfo = {
  id: number
  type: { id: number; name: string; icon: string | null }
  value: string | null
}
export type EmployeeProjectParticipation = {
  id: number
  project: { id: number; name: string; start_date: string | null; end_date: string | null }
  role: { code: string; label: string }
  start_date: string | null
  end_date: string | null
  quotity: string
  is_active: boolean
}
export type EmployeeContractTemporalState = 'current' | 'future' | 'past'
export type EmployeeContractOrganization = {
  id: number
  short_name: string
  name: string
  can_view: boolean
  url: string | null
}
export type EmployeeContractFund = {
  id: number
  display_name: string
  reference: string | null
  project: { id: number; name: string; can_view: boolean; url: string | null }
  funder: EmployeeContractOrganization
  institution: EmployeeContractOrganization
}
export type EmployeeContract = {
  id: number
  employee: EmployeeIdentity
  contract_type: { id: number; name: string } | null
  fund: EmployeeContractFund
  start_date: string | null
  end_date: string | null
  quotity: string
  status: { code: 'effe' | 'prov'; label: string }
  requires_follow_up: boolean
  temporal_state: EmployeeContractTemporalState
}
export type EmployeeContractExpense = {
  id: number
  expense_id: string | null
  date: string
  desc: string | null
  type: { id: number; short_name: string; name: string }
  amount: string
}
export type EmployeeContractDetail = EmployeeContract & {
  expense_count: number
  expense_total: string
  expenses: EmployeeContractExpense[]
}
export type EmployeeContributionTemporalState = 'current' | 'future' | 'past'
export type EmployeeContribution = {
  id: number
  fund: {
    id: number
    display_name: string
    reference: string | null
    project: { id: number; name: string }
  }
  cost_type: { id: number; short_name: string; name: string; is_hr: boolean } | null
  desc: string | null
  start_date: string | null
  end_date: string | null
  quotity: string | null
  amount: string | null
  employee_type: { id: number; code: string; name: string } | null
  contract_types: Array<{ id: number; name: string }>
  temporal_state: EmployeeContributionTemporalState
}
export type EmployeeBudget = {
  id: number
  fund: {
    id: number
    display_name: string
    reference: string | null
    project: { id: number; name: string }
  }
  cost_type: { id: number; short_name: string; name: string; is_hr: boolean } | null
  desc: string | null
  employee_type: { id: number; code: string; name: string } | null
  contract_types: Array<{ id: number; name: string }>
  quotity: string | null
  amount: string | null
  consumed: string | null
  available: string | null
  consumption_ratio: string | null
}
export type ContributionWorkloadItem = {
  id: number
  quotity: string
  fund: { id: number; display_name: string; reference: string | null }
  project: { id: number; name: string }
  cost_type: { id: number; short_name: string; name: string } | null
}
export type ContributionWorkload = {
  range: { start: string | null; end: string | null }
  segments: Array<{
    start: string | null
    end: string | null
    total_quotity: string
    contributions: ContributionWorkloadItem[]
  }>
}
export type EmployeeLeaveType = { id: number; short_name: string; name: string; color: string }
export type LeaveTypeOption = EmployeeLeaveType & { parent_id: number | null; depth: number }
export type LeaveCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type LeaveWrite = {
  type_id: number
  start_date: string
  start_period: 'ST' | 'MI'
  end_date: string
  end_period: 'MI' | 'EN'
  comment: string
}
export type EmployeeLeave = {
  id: number
  type: EmployeeLeaveType
  start_date: string
  start_period: 'ST' | 'MI'
  end_date: string
  end_period: 'MI' | 'EN'
  day_count: number
  comment: string | null
}
export type CalendarEvent = {
  id: string
  title: string
  start: string
  end: string | null
  source: string
  kind: string
  all_day: boolean
  color: string | null
  description: string | null
  display: string
  metadata: Record<string, unknown>
}
export type CalendarFilterType = 'select' | 'checkbox' | 'radio' | 'input-text' | 'input-color'
export type CalendarFilterValue = string | string[] | boolean
export type CalendarFilter = {
  id: string
  title: string
  type: CalendarFilterType
  source: string
  choices: Array<{ value: string | number | boolean; label: string }>
  default: CalendarFilterValue | null
}
export type ProjectWorkloadProject = {
  id: number
  name: string
  quotity: string
  can_view: boolean
}
export type ProjectWorkloadSegment = {
  start: string | null
  end: string | null
  total_quotity: string
  projects: ProjectWorkloadProject[]
}
export type ProjectWorkload = {
  range: { start: string | null; end: string | null }
  segments: ProjectWorkloadSegment[]
}
export type EmployeeMilestoneState = 'completed' | 'overdue' | 'due_soon' | 'planned' | 'in_progress'
export type EmployeeMilestone = {
  id: number
  name: string
  desc: string | null
  start_date: string | null
  end_date: string | null
  status: boolean
  type: 'o' | 'q'
  quotity: string
  display_state: EmployeeMilestoneState
  days_to_due: number | null
  work_kind: 'milestone' | 'task'
  project: { id: number; name: string; can_view: boolean }
  employees: Array<EmployeeIdentity & { can_view: boolean }>
  dependencies: Array<{ id: number; predecessor_id: number; successor_id: number; temporally_inconsistent: boolean }>
}
export type EmployeeListResponse = {
  count: number
  next: string | null
  previous: string | null
  results: EmployeeListItem[]
}
export const employeeSortFields = ['first_name', 'last_name', 'entry_date', 'exit_date', 'is_active'] as const
export type EmployeeSortField = typeof employeeSortFields[number]
export type EmployeeOrdering = EmployeeSortField | `-${EmployeeSortField}`
export type EmployeeListParams = {
  search: string
  filters: URLSearchParams
  ordering: EmployeeOrdering | ''
  limit: number
  offset: number
}

function integer(value: string | null, fallback: number, minimum: number) {
  const number = Number(value)
  return value !== null && /^\d+$/.test(value) && Number.isSafeInteger(number) && number >= minimum ? number : fallback
}

export function readEmployeeParams(query: URLSearchParams): EmployeeListParams {
  query = withFilterDefaults(employeeFilters, query)
  const ordering = query.get('ordering') ?? ''
  return {
    search: query.get('search')?.trim() ?? '',
    filters: readFilterQuery(employeeFilters, query),
    ordering: employeeSortFields.some((field) => ordering === field || ordering === `-${field}`) ? ordering as EmployeeOrdering : '',
    limit: Math.min(integer(query.get('limit'), 25, 1), 250),
    offset: integer(query.get('offset'), 0, 0),
  }
}

export function employeeQuery(params: EmployeeListParams, forApi = false) {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  for (const [parameter, value] of params.filters) {
    if (!forApi || value !== '') query.set(parameter, value)
  }
  if (params.ordering) query.set('ordering', params.ordering)
  if (params.limit !== 25) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (!forApi) query.set(filterDefaultsMarker, '1')
  return query.toString()
}

export function getEmployees(params: EmployeeListParams, signal: AbortSignal) {
  return apiRequest<EmployeeListResponse>(`/api/v1/employees/?${employeeQuery(params, true)}`, { signal })
}

export function getEmployee(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeDetail>(`/api/v1/employees/${encodeURIComponent(id)}/`, { signal })
}

export function getEmployeeStatuses(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeStatusHistoryItem[]>(`/api/v1/employees/${encodeURIComponent(id)}/statuses/`, { signal })
}

export function getEmployeeHierarchy(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeHierarchy>(`/api/v1/employees/${encodeURIComponent(id)}/hierarchy/`, { signal })
}

export function getEmployeeGenericInfo(id: string, signal: AbortSignal) {
  return apiRequest<GenericInfoCollection>(`/api/v1/employees/${encodeURIComponent(id)}/generic-info/`, { signal })
}

export function getEmployeeProjectParticipations(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeProjectParticipation[]>(`/api/v1/employees/${encodeURIComponent(id)}/project-participations/`, { signal })
}

export function getEmployeeProjectWorkload(id: string, range: { start: string; end: string } | 'all', signal: AbortSignal) {
  const query = range === 'all'
    ? 'range=all'
    : new URLSearchParams({ start: range.start, end: range.end }).toString()
  return apiRequest<ProjectWorkload>(`/api/v1/employees/${encodeURIComponent(id)}/project-workload/?${query}`, { signal })
}

export function getEmployeeMilestones(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeMilestone[]>(`/api/v1/employees/${encodeURIComponent(id)}/milestones/`, { signal })
}

export function getEmployeeContracts(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeContract[]>(`/api/v1/employees/${encodeURIComponent(id)}/contracts/`, { signal })
}

export function getEmployeeContract(id: string, contractId: number, signal: AbortSignal) {
  return apiRequest<EmployeeContractDetail>(`/api/v1/employees/${encodeURIComponent(id)}/contracts/${contractId}/`, { signal })
}

export function getEmployeeContributions(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeContribution[]>(`/api/v1/employees/${encodeURIComponent(id)}/contributions/`, { signal })
}

export function getEmployeeBudgets(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeBudget[]>(`/api/v1/employees/${encodeURIComponent(id)}/budgets/`, { signal })
}

export function getEmployeeContributionWorkload(id: string, range: { start: string; end: string } | 'all', signal: AbortSignal) {
  const query = range === 'all'
    ? 'range=all'
    : new URLSearchParams({ start: range.start, end: range.end }).toString()
  return apiRequest<ContributionWorkload>(`/api/v1/employees/${encodeURIComponent(id)}/contribution-workload/?${query}`, { signal })
}

export type EmployeeLeaveFilters = { from?: string; to?: string; type?: string }
function leaveQuery(filters: EmployeeLeaveFilters) {
  const query = new URLSearchParams()
  if (filters.from) query.set('from', filters.from)
  if (filters.to) query.set('to', filters.to)
  if (filters.type) query.set('type', filters.type)
  return query.toString()
}

export function getEmployeeLeaves(id: string, filters: EmployeeLeaveFilters, signal: AbortSignal) {
  const query = leaveQuery(filters)
  return apiRequest<EmployeeLeave[]>(`/api/v1/employees/${encodeURIComponent(id)}/leaves/${query ? `?${query}` : ''}`, { signal })
}

const leaveUrl = (employeeId: string) => `/api/v1/employees/${encodeURIComponent(employeeId)}/leaves/`
export function getLeaveCapabilities(employeeId: string, signal: AbortSignal) {
  return apiRequest<LeaveCapabilities>(`${leaveUrl(employeeId)}capabilities/`, { signal })
}
export function getLeaveTypes(signal: AbortSignal) {
  return apiRequest<LeaveTypeOption[]>('/api/v1/leave-types/', { signal })
}
export function createEmployeeLeave(employeeId: string, value: LeaveWrite) {
  return apiRequest<EmployeeLeave>(leaveUrl(employeeId), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
}
export function updateEmployeeLeave(employeeId: string, leaveId: number, value: LeaveWrite) {
  return apiRequest<EmployeeLeave>(`${leaveUrl(employeeId)}${leaveId}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
}
export function deleteEmployeeLeave(employeeId: string, leaveId: number) {
  return apiRequest<void>(`${leaveUrl(employeeId)}${leaveId}/`, { method: 'DELETE' })
}

export function getEmployeeCalendarFilters(id: string, signal: AbortSignal, context?: 'employee-gantt') {
  return apiRequest<CalendarFilter[]>(`/api/v1/employees/${encodeURIComponent(id)}/calendar/filters/${context ? `?context=${context}` : ''}`, { signal })
}

export function getEmployeeCalendar(id: string, range: { from: string; to: string }, type: string, calendarFilters: Record<string, CalendarFilterValue>, signal: AbortSignal, context?: 'employee-gantt') {
  const query = new URLSearchParams(leaveQuery({ ...range, type: type || undefined }))
  if (context) query.set('context', context)
  for (const [id, value] of Object.entries(calendarFilters)) {
    const serialized = Array.isArray(value) ? value.join(',') : String(value)
    if (serialized) query.set(id, serialized)
  }
  return apiRequest<CalendarEvent[]>(`/api/v1/employees/${encodeURIComponent(id)}/calendar/?${query.toString()}`, { signal })
}

export type GenericInfoType = EmployeeGenericInfo['type']
export type GenericInfoCollection = {
  capabilities: { can_add: boolean; can_change: boolean; can_delete: boolean }
  items: EmployeeGenericInfo[]
}

export function getGenericInfoTypes(signal: AbortSignal) {
  return apiRequest<GenericInfoType[]>('/api/v1/generic-info-types/', { signal })
}

export function createEmployeeGenericInfo(id: string, data: { type_id: number; value: string | null }) {
  return apiRequest<EmployeeGenericInfo>(`/api/v1/employees/${encodeURIComponent(id)}/generic-info/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
}

export function updateEmployeeGenericInfo(id: string, infoId: number, value: string | null) {
  return apiRequest<EmployeeGenericInfo>(`/api/v1/employees/${encodeURIComponent(id)}/generic-info/${infoId}/`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }),
  })
}

export function deleteEmployeeGenericInfo(id: string, infoId: number) {
  return apiRequest<void>(`/api/v1/employees/${encodeURIComponent(id)}/generic-info/${infoId}/`, { method: 'DELETE' })
}
