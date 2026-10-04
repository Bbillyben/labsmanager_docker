import { apiRequest } from './client'
import { filterDefaultsMarker, readFilterQuery } from '../filters/url'
import { financialFilters, type FinancialKind } from '../config/financialFilters'
import type { ProjectBudget } from './projectBudgets'

export type Relation = { id: number; name: string; can_view: boolean }
export type FinancialFund = { project: Relation; funder: Relation; institution: Relation; ref: string; start_date: string | null; end_date: string | null; is_active: boolean }
export type FundItemRow = { id: number; admin_url: string | null; fund: FinancialFund; type: { id: number; name: string; short_name: string }; entry_date: string; value_date: string; amount: string; expense: string; available: string; contract_count: number | null }
export type BudgetRow = Omit<ProjectBudget, 'fund' | 'employee'> & { fund: FinancialFund; employee: (ProjectBudget['employee'] & { can_view: boolean }) | null }
export type ExpenseRow = { id: number; admin_url: string | null; fund: FinancialFund; expense_id: string; desc: string; date: string; type: FundItemRow['type']; amount: string; status: 'e' | 'r' | 'p' }
export type FinancialRow = FundItemRow | BudgetRow | ExpenseRow
export type FinancialList<T> = { count: number; next: string | null; previous: string | null; results: T[] }
export type FinancialOptions = { cost_types: Array<{ id: number; name: string }>; contract_types: Array<{ id: number; name: string }>; employee_types: Array<{ id: number; name: string }>; statuses: Array<{ value: string; label: string }> }
export type FinancialContract = { id: number; employee: string; type: string | null; status: 'effe' | 'prov'; start_date: string | null; end_date: string | null; quotity: string; is_active: boolean }

const sortFields: Record<FinancialKind, readonly string[]> = {
  'fund-items': ['fund__project__name', 'fund__funder__short_name', 'fund__institution__short_name', 'fund__start_date', 'fund__end_date', 'fund__ref', 'type__name', 'amount', 'expense', '_available'],
  budgets: ['fund__project__name', 'cost_type__name', 'fund__funder__short_name', 'fund__institution__short_name', 'fund__ref', 'amount', 'expense', '_available', 'emp_type__name', 'employee__last_name'],
  expenses: ['expense_id', 'desc', 'type__name', 'amount', 'status', 'date', 'fund_item__project__name', 'fund_item__ref'],
}
const defaultSort: Record<FinancialKind, string> = { 'fund-items': 'fund__project__name', budgets: 'fund__project__name', expenses: '-date' }
const positiveInt = (value: string | null, fallback: number) => value !== null && /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) ? Number(value) : fallback

export function financialQuery(kind: FinancialKind, query: URLSearchParams, forApi = false) {
  const result = readFilterQuery(financialFilters(kind), query)
  const ordering = query.get('ordering') ?? defaultSort[kind]
  if (sortFields[kind].some((field) => ordering === field || ordering === `-${field}`) && ordering !== defaultSort[kind]) result.set('ordering', ordering)
  const limit = Math.min(Math.max(positiveInt(query.get('limit'), 25), 1), 250)
  const offset = positiveInt(query.get('offset'), 0)
  if (limit !== 25) result.set('limit', String(limit))
  if (offset) result.set('offset', String(offset))
  if (!forApi) result.set(filterDefaultsMarker, '1')
  else for (const [key, value] of [...result]) if (!value) result.delete(key)
  return result.toString()
}

export const getFinancialList = <T extends FinancialRow>(kind: FinancialKind, query: string, signal: AbortSignal) => apiRequest<FinancialList<T>>(`/api/v1/${kind}/?${financialQuery(kind, new URLSearchParams(query), true)}`, { signal })
export const getFinancialOptions = (signal: AbortSignal) => apiRequest<FinancialOptions>('/api/v1/financial/filter-options/', { signal })
export const getFundItemContracts = (id: number, signal: AbortSignal) => apiRequest<FinancialContract[]>(`/api/v1/fund-items/${id}/contracts/`, { signal })
export const financialSortFields = sortFields
export const financialDefaultSort = defaultSort
