import { apiRequest } from './client'
import { projectFilters } from '../config/projectFilters'
import { filterDefaultsMarker, readFilterQuery, withFilterDefaults } from '../filters/url'

export type ProjectCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type ProjectItem = {
  id: number
  name: string
  start_date: string | null
  end_date: string | null
  status: boolean
  institutions: string[]
  participants: string[]
  funds: string[]
  capabilities: ProjectCapabilities
}
export type ProjectWrite = { name: string; start_date: string | null; end_date: string | null; status: boolean }
export type ProjectResponse = { id: number; name: string; start_date: string | null; end_date: string | null; status: boolean }
export type ProjectListResponse = { count: number; next: string | null; previous: string | null; results: ProjectItem[] }
export type ProjectFilterOptions = { funders: Array<{ id: number; short_name: string }>; institutions: Array<{ id: number; short_name: string }>; teams: Array<{ id: number; name: string }> }
export const projectSortFields = ['name', 'start_date', 'end_date', 'status'] as const
export type ProjectSortField = typeof projectSortFields[number]
export type ProjectOrdering = ProjectSortField | `-${ProjectSortField}`
export type ProjectListParams = { search: string; filters: URLSearchParams; ordering: ProjectOrdering; limit: number; offset: number }

function integer(value: string | null, fallback: number, minimum: number) {
  const number = Number(value)
  return value !== null && /^\d+$/.test(value) && Number.isSafeInteger(number) && number >= minimum ? number : fallback
}

export function readProjectParams(raw: URLSearchParams): ProjectListParams {
  const query = withFilterDefaults(projectFilters, raw)
  const ordering = query.get('ordering') ?? 'name'
  return {
    search: query.get('search')?.trim() ?? '',
    filters: readFilterQuery(projectFilters, query),
    ordering: projectSortFields.some((field) => ordering === field || ordering === `-${field}`) ? ordering as ProjectOrdering : 'name',
    limit: Math.min(integer(query.get('limit'), 25, 1), 250),
    offset: integer(query.get('offset'), 0, 0),
  }
}

export function projectQuery(params: ProjectListParams, forApi = false) {
  const query = new URLSearchParams()
  if (params.search) query.set('search', params.search)
  for (const [parameter, value] of params.filters) if (!forApi || value !== '') query.set(parameter, value)
  if (params.ordering !== 'name') query.set('ordering', params.ordering)
  if (params.limit !== 25) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (!forApi) query.set(filterDefaultsMarker, '1')
  return query.toString()
}

export function getProjects(params: ProjectListParams, signal: AbortSignal) {
  return apiRequest<ProjectListResponse>(`/api/v1/projects/?${projectQuery(params, true)}`, { signal })
}
export function getProject(id: number, signal: AbortSignal) { return apiRequest<ProjectItem>(`/api/v1/projects/${id}/`, { signal }) }
export function getProjectCapabilities(signal: AbortSignal) { return apiRequest<ProjectCapabilities>('/api/v1/projects/capabilities/', { signal }) }
export function getProjectFilterOptions(signal: AbortSignal) { return apiRequest<ProjectFilterOptions>('/api/v1/projects/filter-options/', { signal }) }
export function createProject(value: ProjectWrite) { return apiRequest<ProjectResponse>('/api/v1/projects/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }) }
export function updateProject(id: number, value: ProjectWrite) { return apiRequest<ProjectResponse>(`/api/v1/projects/${id}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }) }
export function deleteProject(id: number) { return apiRequest<void>(`/api/v1/projects/${id}/`, { method: 'DELETE' }) }
