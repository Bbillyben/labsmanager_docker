import { apiRequest } from './client'

export type FundingCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type CostType = { id: number; short_name: string; name: string }
export type FundingInstitution = { id: number; short_name: string; name: string }
export type Amounts = { amount: string; expense: string; available: string }
export type Fund = Amounts & { admin_url?: string | null; id: number; funder: FundingInstitution; institution: FundingInstitution; ref: string; start_date: string | null; end_date: string | null; is_active: boolean; capabilities: FundingCapabilities }
export type FundingRow = { type: CostType; cells: Record<string, Amounts>; total: Amounts }
export type FundingOverview = { rows: FundingRow[]; fund_totals: Record<string, Amounts>; grand_total: Amounts }
export type ProjectFunding = { capabilities: Pick<FundingCapabilities, 'can_add'>; project_dates: { start_date: string | null; end_date: string | null }; funds: Fund[]; overview: FundingOverview }
export type FundItem = Amounts & { admin_url?: string | null; id: number; type: CostType; entry_date: string; value_date: string }
export type ExpensePoint = { admin_url?: string | null; id: number; type: CostType; entry_date: string; value_date: string; amount: string }
export type ExpensePointCapabilities = FundingCapabilities & { expense_mode: 's' | 'e' | 'h' }
export type FundDetail = { fund: Fund; summary: FundingRow[]; total: Amounts; items: { capabilities: FundingCapabilities; items: FundItem[] }; expense_points: { capabilities: ExpensePointCapabilities; items: ExpensePoint[] } }
export type FundingOptions = { funders: FundingInstitution[]; institutions: FundingInstitution[]; cost_types: CostType[]; project_dates: ProjectFunding['project_dates'] }
export type FundWrite = { funder_id?: number; institution_id?: number; start_date: string | null; end_date: string | null; ref: string; update_project_end?: boolean }
export type FundChildWrite = { type_id?: number; amount: string; entry_date: string; value_date: string }

const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/funding/`
const fundPath = (projectId: string, fundId: number) => `${base(projectId)}funds/${fundId}/`
const childPath = (projectId: string, fundId: number, kind: 'items' | 'expense-points', itemId?: number) => `${fundPath(projectId, fundId)}${kind}/${itemId === undefined ? '' : `${itemId}/`}`
const write = (method: 'POST' | 'PATCH', body: object) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const getProjectFunding = (projectId: string, signal: AbortSignal) => apiRequest<ProjectFunding>(base(projectId), { signal })
export const getFundingOptions = (projectId: string, signal: AbortSignal) => apiRequest<FundingOptions>(`${base(projectId)}options/`, { signal })
export const getFundDetail = (projectId: string, fundId: number, signal: AbortSignal) => apiRequest<FundDetail>(fundPath(projectId, fundId), { signal })
export const createFund = (projectId: string, value: FundWrite) => apiRequest<Fund>(base(projectId), write('POST', value))
export const updateFund = (projectId: string, fundId: number, value: FundWrite) => apiRequest<Fund>(fundPath(projectId, fundId), write('PATCH', value))
export const deleteFund = (projectId: string, fundId: number) => apiRequest<void>(fundPath(projectId, fundId), { method: 'DELETE' })
export const createFundItem = (projectId: string, fundId: number, value: FundChildWrite) => apiRequest<FundItem>(childPath(projectId, fundId, 'items'), write('POST', value))
export const updateFundItem = (projectId: string, fundId: number, itemId: number, value: FundChildWrite) => apiRequest<FundItem>(childPath(projectId, fundId, 'items', itemId), write('PATCH', value))
export const deleteFundItem = (projectId: string, fundId: number, itemId: number) => apiRequest<void>(childPath(projectId, fundId, 'items', itemId), { method: 'DELETE' })
export const createExpensePoint = (projectId: string, fundId: number, value: FundChildWrite) => apiRequest<ExpensePoint>(childPath(projectId, fundId, 'expense-points'), write('POST', value))
export const updateExpensePoint = (projectId: string, fundId: number, itemId: number, value: FundChildWrite) => apiRequest<ExpensePoint>(childPath(projectId, fundId, 'expense-points', itemId), write('PATCH', value))
export const deleteExpensePoint = (projectId: string, fundId: number, itemId: number) => apiRequest<void>(childPath(projectId, fundId, 'expense-points', itemId), { method: 'DELETE' })
