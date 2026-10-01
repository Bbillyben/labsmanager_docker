import { apiRequest } from './client'
import type { CostType } from './funding'

export type BudgetKind = 'budget' | 'contribution'
export type NamedId = { id: number; name: string }
export type BudgetCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type BudgetBase = {
  admin_url?: string | null
  id: number
  fund: NamedId
  cost_type: CostType | null
  desc: string
  emp_type: NamedId | null
  employee: NamedId | null
  contract_types: NamedId[]
  quotity: string | null
  amount: string
  capabilities: BudgetCapabilities
}
export type ProjectBudget = BudgetBase & { expense: string; available: string | null; consumption_ratio: string | null }
export type ProjectContribution = BudgetBase & { start_date: string | null; end_date: string | null }
export type BudgetCollection<T> = { capabilities: BudgetCapabilities; items: T[] }
export type BudgetOptions = { funds: NamedId[]; cost_types: CostType[]; employee_types: NamedId[]; contract_types: NamedId[]; employees: NamedId[] }
export type BudgetWrite = {
  fund_id?: number
  cost_type_id?: number
  amount?: string
  emp_type_id?: number | null
  employee_id?: number | null
  contract_type_ids?: number[]
  quotity?: string | null
  desc?: string
  start_date?: string | null
  end_date?: string | null
}

const base = (projectId: string, kind: BudgetKind) => `/api/v1/projects/${projectId}/${kind === 'budget' ? 'budgets' : 'contributions'}/`
const write = (method: 'POST' | 'PATCH', body: BudgetWrite) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export function getProjectBudgetCollection(projectId: string, kind: BudgetKind, signal: AbortSignal) {
  return apiRequest<BudgetCollection<ProjectBudget | ProjectContribution>>(base(projectId, kind), { signal })
}
export const getProjectBudgetOptions = (projectId: string, kind: BudgetKind, signal: AbortSignal) => apiRequest<BudgetOptions>(`${base(projectId, kind)}options/`, { signal })
export const getProjectBudgetDetail = (projectId: string, kind: BudgetKind, id: number, signal: AbortSignal) => apiRequest<ProjectBudget | ProjectContribution>(`${base(projectId, kind)}${id}/`, { signal })
export const createProjectBudget = (projectId: string, kind: BudgetKind, body: BudgetWrite) => apiRequest<ProjectBudget | ProjectContribution>(base(projectId, kind), write('POST', body))
export const updateProjectBudget = (projectId: string, kind: BudgetKind, id: number, body: BudgetWrite) => apiRequest<ProjectBudget | ProjectContribution>(`${base(projectId, kind)}${id}/`, write('PATCH', body))
export const deleteProjectBudget = (projectId: string, kind: BudgetKind, id: number) => apiRequest<void>(`${base(projectId, kind)}${id}/`, { method: 'DELETE' })
