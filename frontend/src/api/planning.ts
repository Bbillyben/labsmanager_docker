import { apiRequest } from './client'

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
export type PlanningDependencies = { can_add: boolean; predecessors: PlanningDependency[] }

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
