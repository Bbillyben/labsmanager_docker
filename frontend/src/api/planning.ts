import { apiRequest } from './client'

export type PlanningMilestoneState = 'completed' | 'overdue' | 'due_soon' | 'planned' | 'in_progress'
export type PlanningMilestone = {
  id: number
  name: string
  desc: string | null
  start_date: string | null
  end_date: string | null
  status: boolean
  type: 'o' | 'q'
  quotity: string
  display_state: PlanningMilestoneState
  days_to_due: number | null
  work_kind: 'milestone' | 'task'
  project: { id: number; name: string; can_view: boolean }
  employees: Array<{ id: number; first_name: string; last_name: string; can_view: boolean }>
  dependencies: Array<{ id: number; predecessor_id: number; successor_id: number; temporally_inconsistent: boolean }>
  can_change?: boolean
}
export type EmployeeMilestoneWrite = { desc?: string | null; quotity?: string; status?: boolean }
export type PlanningFilters = { search?: string; kind?: PlanningMilestone['work_kind']; employee?: string }
export type ProjectPlanningCollection = {
  capabilities: { can_add: boolean; can_change: boolean; can_delete: boolean }
  participants: Array<{ id: number; first_name: string; last_name: string }>
  items: PlanningMilestone[]
}
export type PlanningMilestoneWrite = {
  name: string; desc: string | null; work_kind: PlanningMilestone['work_kind']
  start_date?: string | null; end_date: string | null; type: PlanningMilestone['type']
  quotity: string; status: boolean; employee_ids: number[]
}

export function planningFilterQuery(filters: PlanningFilters = {}) {
  const params = new URLSearchParams()
  if (filters.search?.trim()) params.set('search', filters.search.trim())
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.employee) params.set('employee', filters.employee)
  const query = params.toString()
  return query ? `?${query}` : ''
}

const projectPlanningUrl = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/planning/`
export function getProjectPlanning(projectId: string, filters: PlanningFilters, signal: AbortSignal) {
  return apiRequest<ProjectPlanningCollection>(`${projectPlanningUrl(projectId)}${planningFilterQuery(filters)}`, { signal })
}
export function createProjectPlanningItem(projectId: string, data: PlanningMilestoneWrite) {
  return apiRequest<PlanningMilestone>(projectPlanningUrl(projectId), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
}
export function updateProjectPlanningItem(projectId: string, itemId: number, data: PlanningMilestoneWrite) {
  return apiRequest<PlanningMilestone>(`${projectPlanningUrl(projectId)}${itemId}/`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
}
export function deleteProjectPlanningItem(projectId: string, itemId: number) {
  return apiRequest<void>(`${projectPlanningUrl(projectId)}${itemId}/`, { method: 'DELETE' })
}

export type PlanningProject = { id: number; name: string }
export type PlanningItem = {
  id: number
  name: string
  work_kind: 'task' | 'milestone'
  start_date: string | null
  end_date: string | null
  project: PlanningProject
}
export type PlanningDependency = {
  id: number
  predecessor: PlanningItem
  successor_id: number
  temporally_inconsistent: boolean
  can_delete: boolean
}
export type PlanningSuccessorDependency = {
  id: number
  successor: PlanningItem
  predecessor_id: number
  temporally_inconsistent: boolean
}
export type PlanningDependencies = { can_add: boolean; predecessors: PlanningDependency[]; successors: PlanningSuccessorDependency[] }

const itemUrl = (id: number) => `/api/v1/planning/items/${id}/dependencies/`

export function getPlanningDependencies(id: number, signal: AbortSignal) {
  return apiRequest<PlanningDependencies>(itemUrl(id), { signal })
}

export function getEditablePlanningProjects(search: string, preferred: number, signal: AbortSignal) {
  const query = new URLSearchParams({ search, preferred: String(preferred) })
  return apiRequest<PlanningProject[]>(`/api/v1/planning/projects/?${query}`, { signal })
}

export function getProjectPlanningItems(projectId: number, search: string, exclude: number, signal: AbortSignal) {
  const query = new URLSearchParams({ search, exclude: String(exclude) })
  return apiRequest<PlanningItem[]>(`/api/v1/planning/projects/${projectId}/items/?${query}`, { signal })
}

export function createPlanningDependency(successorId: number, predecessorId: number) {
  return apiRequest<PlanningDependency>(itemUrl(successorId), {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predecessor_id: predecessorId }),
  })
}

export function deletePlanningDependency(successorId: number, dependencyId: number) {
  return apiRequest<void>(`${itemUrl(successorId)}${dependencyId}/`, { method: 'DELETE' })
}
