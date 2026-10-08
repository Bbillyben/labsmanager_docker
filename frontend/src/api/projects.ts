import { apiRequest } from './client'
import { projectFilters } from '../config/projectFilters'
import { filterDefaultsMarker, readFilterQuery, withFilterDefaults } from '../filters/url'

export type ProjectCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean; can_export_word?: boolean; can_export_pdf?: boolean; can_change_settings?: boolean }
export type ProjectItem = {
  admin_url?: string | null
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
export type ProjectResponse = { admin_url?: string | null; id: number; name: string; start_date: string | null; end_date: string | null; status: boolean }
export type ProjectListResponse = { count: number; next: string | null; previous: string | null; results: ProjectItem[] }
export type ProjectChildCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type ProjectCollection<T> = { capabilities: ProjectChildCapabilities; items: T[] }
export type ProjectGenericInfo = { id: number; type: { id: number; name: string; icon: string | null }; value: string | null }
export type ProjectInstitution = { id: number; institution: { id: number; short_name: string; name: string }; status: 'c' | 'p'; status_label: string }
export type ProjectParticipant = { id: number; employee: { id: number; first_name: string; last_name: string; is_active: boolean; can_view: boolean }; status: 'l' | 'cl' | 'p'; status_label: string; start_date: string | null; end_date: string | null; quotity: string; is_active: boolean }
export type ProjectOverview = ProjectResponse & { capabilities: ProjectCapabilities; funding_visible: boolean; generic_info: ProjectCollection<ProjectGenericInfo>; institutions: ProjectCollection<ProjectInstitution>; participants: ProjectCollection<ProjectParticipant> }
export type ProjectOverviewOptions = { generic_info_types: Array<{ id: number; name: string; icon: string | null }>; institutions: Array<{ id: number; short_name: string; name: string }> }
export type ProjectParticipantWrite = { employee_id?: number; status: ProjectParticipant['status']; start_date: string | null; end_date: string | null; quotity: string }
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
  const query = withFilterDefaults(projectFilters(), raw)
  const ordering = query.get('ordering') ?? 'name'
  return {
    search: query.get('search')?.trim() ?? '',
    filters: readFilterQuery(projectFilters(), query),
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
export function getProject(id: string, signal: AbortSignal) { return apiRequest<ProjectOverview>(`/api/v1/projects/${encodeURIComponent(id)}/`, { signal }) }
export function getProjectOverviewOptions(id: string, signal: AbortSignal) { return apiRequest<ProjectOverviewOptions>(`/api/v1/projects/${encodeURIComponent(id)}/overview-options/`, { signal }) }
const childPath = (id: string, resource: string) => `/api/v1/projects/${encodeURIComponent(id)}/${resource}/`
const itemPath = (id: string, resource: string, itemId: number) => `${childPath(id, resource)}${itemId}/`
const jsonWrite = (method: 'POST' | 'PATCH', body: object) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export function createProjectGenericInfo(id: string, value: { type_id: number; value: string }) { return apiRequest<ProjectGenericInfo>(childPath(id, 'generic-info'), jsonWrite('POST', value)) }
export function updateProjectGenericInfo(id: string, itemId: number, value: string) { return apiRequest<ProjectGenericInfo>(itemPath(id, 'generic-info', itemId), jsonWrite('PATCH', { value })) }
export function deleteProjectGenericInfo(id: string, itemId: number) { return apiRequest<void>(itemPath(id, 'generic-info', itemId), { method: 'DELETE' }) }
export function createProjectInstitution(id: string, value: { institution_id: number; status: ProjectInstitution['status'] }) { return apiRequest<ProjectInstitution>(childPath(id, 'institutions'), jsonWrite('POST', value)) }
export function updateProjectInstitution(id: string, itemId: number, value: { status: ProjectInstitution['status'] }) { return apiRequest<ProjectInstitution>(itemPath(id, 'institutions', itemId), jsonWrite('PATCH', value)) }
export function deleteProjectInstitution(id: string, itemId: number) { return apiRequest<void>(itemPath(id, 'institutions', itemId), { method: 'DELETE' }) }
export function createProjectParticipant(id: string, value: ProjectParticipantWrite) { return apiRequest<ProjectParticipant>(childPath(id, 'participants'), jsonWrite('POST', value)) }
export function updateProjectParticipant(id: string, itemId: number, value: ProjectParticipantWrite) { return apiRequest<ProjectParticipant>(itemPath(id, 'participants', itemId), jsonWrite('PATCH', value)) }
export function deleteProjectParticipant(id: string, itemId: number) { return apiRequest<void>(itemPath(id, 'participants', itemId), { method: 'DELETE' }) }
export function getProjectCapabilities(signal: AbortSignal) { return apiRequest<ProjectCapabilities>('/api/v1/projects/capabilities/', { signal }) }
export function getProjectFilterOptions(signal: AbortSignal) { return apiRequest<ProjectFilterOptions>('/api/v1/projects/filter-options/', { signal }) }
export function createProject(value: ProjectWrite) { return apiRequest<ProjectResponse>('/api/v1/projects/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }) }
export function updateProject(id: number, value: Partial<ProjectWrite>) { return apiRequest<ProjectResponse>(`/api/v1/projects/${id}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) }) }
export function deleteProject(id: number) { return apiRequest<void>(`/api/v1/projects/${id}/`, { method: 'DELETE' }) }
