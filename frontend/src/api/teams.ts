import { apiRequest } from './client'
import { teamFilters } from '../config/teamFilters'
import { filterDefaultsMarker, readFilterQuery } from '../filters/url'

export type TeamEmployee = { id: number; name: string; can_view: boolean }
export type TeamMate = { admin_url?: string | null; id: number; employee: TeamEmployee; start_date: string | null; end_date: string | null; is_active: boolean; capabilities: { can_change: boolean; can_delete: boolean } }
export type Team = {
  admin_url?: string | null
  id: number; name: string; leader: TeamEmployee; mates: TeamMate[]
  capabilities: { can_view: boolean; can_change: boolean; can_manage_composition: boolean }
}
export type TeamProject = { id: number; name: string; start_date: string | null; end_date: string | null; status: boolean }
export type TeamBudget = {
  id: number; project: { id: number; name: string }; fund: { id: number; name: string }
  cost_type: { id: number; short_name: string; name: string } | null
  desc: string; amount: string; expense: string; available: string | null
  capabilities: { can_add: false; can_change: false; can_delete: false }
}
export type TeamListResponse = { count: number; next: string | null; previous: string | null; results: Team[]; capabilities: { can_add: boolean; can_choose_leader: boolean; default_leader: { id: number; name: string } | null } }
export type TeamWrite = { name: string; leader_id: number }
export type TeamMateWrite = { employee_id: number; start_date: string | null; end_date: string | null }
export type TeamOrdering = 'name' | '-name' | 'leader__last_name' | '-leader__last_name'
export type TeamListParams = { filters: URLSearchParams; ordering: TeamOrdering; limit: number; offset: number }
const orderings: TeamOrdering[] = ['name', '-name', 'leader__last_name', '-leader__last_name']
const integer = (value: string | null, fallback: number) => value !== null && /^\d+$/.test(value) && Number(value) >= 0 ? Number(value) : fallback
export function readTeamParams(query: URLSearchParams): TeamListParams {
  const ordering = query.get('ordering') ?? 'name'
  return { filters: readFilterQuery(teamFilters(), query), ordering: orderings.includes(ordering as TeamOrdering) ? ordering as TeamOrdering : 'name', limit: Math.min(Math.max(integer(query.get('limit'), 25), 1), 250), offset: integer(query.get('offset'), 0) }
}
export function teamQuery(params: TeamListParams, forApi = false) {
  const query = new URLSearchParams()
  for (const [key, value] of params.filters) if (!forApi || value) query.set(key, value)
  if (params.ordering !== 'name') query.set('ordering', params.ordering)
  if (params.limit !== 25) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (!forApi) query.set(filterDefaultsMarker, '1')
  return query.toString()
}
const base = (id: string) => `/api/v1/teams/${encodeURIComponent(id)}/`
export const getTeams = (params: TeamListParams, signal: AbortSignal) => apiRequest<TeamListResponse>(`/api/v1/teams/?${teamQuery(params, true)}`, { signal })
export const getTeam = (id: string, signal: AbortSignal) => apiRequest<Team>(base(id), { signal })
export const getTeamProjects = (id: string, signal: AbortSignal) => apiRequest<TeamProject[]>(`${base(id)}projects/`, { signal })
export const getTeamBudgets = (id: string, signal: AbortSignal) => apiRequest<TeamBudget[]>(`${base(id)}budgets/`, { signal })
export const createTeam = (data: TeamWrite) => apiRequest<Team>('/api/v1/teams/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const updateTeam = (id: string, data: TeamWrite) => apiRequest<Team>(base(id), { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const addTeamMate = (id: string, data: TeamMateWrite) => apiRequest<{ id: number }>(`${base(id)}mates/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const updateTeamMate = (id: string, mateId: number, data: TeamMateWrite) => apiRequest<TeamMate>(`${base(id)}mates/${mateId}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
export const removeTeamMate = (id: string, mateId: number) => apiRequest<void>(`${base(id)}mates/${mateId}/`, { method: 'DELETE' })
