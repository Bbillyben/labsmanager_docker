import { apiRequest } from './client'
import type { CostType } from './funding'

export type ExpenseCapabilities = { can_change: boolean; can_delete: boolean }
export type Expense = { id: number; expense_id: string; desc: string; date: string; type: CostType; amount: string; status: 'e' | 'r' | 'p'; contract: { id: number; name: string } | null; budget: { id: number; name: string } | null; capabilities: ExpenseCapabilities }
export type ExpenseCollection = { count: number; next: string | null; previous: string | null; results: Expense[]; capabilities: { expense_mode: 's' | 'e' | 'h'; can_add: boolean; can_sync_expenses: boolean } }
export type ExpenseOptions = { cost_types: CostType[]; hr_type_ids: number[]; contracts: Array<{ id: number; name: string }>; budgets: Array<{ id: number; name: string }> }
export type ExpenseWrite = { expense_id: string; desc: string; date: string; type_id: number | undefined; amount: string; status: Expense['status']; contract_id: number | null; budget_id: number | null }
export type ExpenseScope = { fundId: number; employeeId?: never; contractId?: never; projectId?: never; budgetId?: never }
  | { employeeId: number; contractId: number; fundId?: never; projectId?: never; budgetId?: never }
  | { projectId: string; contractId: number; fundId?: never; employeeId?: never; budgetId?: never }
  | { projectId: string; budgetId: number; fundId?: never; employeeId?: never; contractId?: never }
export type ExpenseFilters = { search: string; type: string; date_from: string; date_to: string; page: number }

const base = (scope: ExpenseScope) => 'budgetId' in scope
  ? `/api/v1/projects/${scope.projectId}/budgets/${scope.budgetId}/expenses/`
  : 'fundId' in scope
    ? `/api/v1/funds/${scope.fundId}/expenses/`
    : 'projectId' in scope
      ? `/api/v1/projects/${scope.projectId}/contracts/${scope.contractId}/expenses/`
    : `/api/v1/employees/${scope.employeeId}/contracts/${scope.contractId}/expenses/`

const write = (method: 'POST' | 'PATCH', body: Partial<ExpenseWrite>) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export function getExpenses(scope: ExpenseScope, filters: ExpenseFilters, signal: AbortSignal) {
  const query = new URLSearchParams()
  for (const key of ['search', 'type', 'date_from', 'date_to'] as const) if (filters[key]) query.set(key, filters[key])
  query.set('page', String(filters.page))
  return apiRequest<ExpenseCollection>(`${base(scope)}?${query}`, { signal })
}
export const getExpenseOptions = (scope: ExpenseScope, signal: AbortSignal) => apiRequest<ExpenseOptions>(`${base(scope)}options/`, { signal })
export const createExpense = (scope: ExpenseScope, body: ExpenseWrite) => apiRequest<Expense>(base(scope), write('POST', body))
export const updateExpense = (scope: ExpenseScope, id: number, body: ExpenseWrite) => apiRequest<Expense>(`${base(scope)}${id}/`, write('PATCH', body))
export const deleteExpense = (scope: ExpenseScope, id: number) => apiRequest<void>(`${base(scope)}${id}/`, { method: 'DELETE' })
export const syncExpenses = (fundId: number) => apiRequest<{ detail: string }>(`/api/v1/funds/${fundId}/expenses/sync/`, { method: 'POST' })
