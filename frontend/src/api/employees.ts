import { apiRequest } from './client'
import { employeeFilters } from '../config/employeeFilters'
import { readFilterQuery } from '../filters/url'

export type EmployeeIdentity = { id: number; first_name: string; last_name: string }
export type EmployeeStatus = { id: number; code: string; name: string }
export type EmployeeListItem = EmployeeIdentity & {
  entry_date: string | null
  exit_date: string | null
  is_active: boolean
  current_statuses: EmployeeStatus[]
  superiors: EmployeeIdentity[]
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
  return query.toString()
}

export function getEmployees(params: EmployeeListParams, signal: AbortSignal) {
  return apiRequest<EmployeeListResponse>(`/api/v1/employees/?${employeeQuery(params, true)}`, { signal })
}

export function getEmployee(id: string, signal: AbortSignal) {
  return apiRequest<EmployeeListItem>(`/api/v1/employees/${encodeURIComponent(id)}/`, { signal })
}
