import { apiRequest } from './client'
import type { EmployeeContract } from './employees'
import { contractFilters } from '../config/contractFilters'
import { filterDefaultsMarker, readFilterQuery } from '../filters/url'

export type ContractScope = { projectId: string; employeeId?: never; hubContractId?: never } | { employeeId: string; projectId?: never; hubContractId?: never } | { hubContractId: number; projectId?: never; employeeId?: never }
export type ContractCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type EmployeeEndDateSyncOffer = { employee_id: number; current_end_date: string | null; proposed_end_date: string; can_update: boolean }
export type ContractRecord = EmployeeContract & {
  admin_url?: string | null
  capabilities: ContractCapabilities
  notes: { visible_count: number; can_add: boolean }
  employee_end_date_sync?: EmployeeEndDateSyncOffer | null
  total_amount?: string
  remain_amount?: string
  man_month?: string
}
export type ContractCollection = { items: ContractRecord[]; capabilities: ContractCapabilities }
export type ContractOptions = {
  employees: Array<{ id: number; name: string }>
  funds: Array<{ id: number; name: string; project_id: number }>
  contract_types: Array<{ id: number; name: string }>
}
export type ContractWrite = {
  employee_id?: number
  fund_id?: number
  contract_type_id?: number | null
  start_date?: string | null
  end_date?: string | null
  quotity?: string
  status?: 'effe' | 'prov'
  is_active?: boolean
}

export type ContractHubItem = EmployeeContract & { is_active: boolean; total_amount: string; capabilities: { can_change: boolean }; notes: ContractRecord['notes']; admin_url?: string | null }
export type ContractHubListResponse = { count: number; next: string | null; previous: string | null; results: ContractHubItem[] }
export type ContractHubOptions = { contract_types: Array<{ id: number; name: string }>; statuses: Array<{ value: string; label: string }>; funders: Array<{ id: number; short_name: string }>; institutions: Array<{ id: number; short_name: string }> }
export const contractHubSortFields = ['employee__last_name', 'contract_type__name', 'status', 'start_date', 'end_date', 'fund__project__name', 'hub_total_amount'] as const
export type ContractHubOrdering = typeof contractHubSortFields[number] | `-${typeof contractHubSortFields[number]}`
export type ContractHubParams = { filters: URLSearchParams; ordering: ContractHubOrdering; limit: number; offset: number }
const positiveInt = (value: string | null, fallback: number) => value !== null && /^\d+$/.test(value) && Number.isSafeInteger(Number(value)) ? Number(value) : fallback
export function readContractHubParams(query: URLSearchParams): ContractHubParams {
  const ordering = query.get('ordering') ?? 'employee__last_name'
  return { filters: readFilterQuery(contractFilters(), query), ordering: contractHubSortFields.some((field) => ordering === field || ordering === `-${field}`) ? ordering as ContractHubOrdering : 'employee__last_name', limit: Math.min(Math.max(positiveInt(query.get('limit'), 25), 1), 250), offset: positiveInt(query.get('offset'), 0) }
}
export function contractHubQuery(params: ContractHubParams, forApi = false) {
  const query = new URLSearchParams()
  for (const [key, value] of params.filters) if (!forApi || value) query.set(key, value)
  if (params.ordering !== 'employee__last_name') query.set('ordering', params.ordering)
  if (params.limit !== 25) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (!forApi) query.set(filterDefaultsMarker, '1')
  return query.toString()
}
export const getContractHub = (params: ContractHubParams, signal: AbortSignal) => apiRequest<ContractHubListResponse>(`/api/v1/contracts/?${contractHubQuery(params, true)}`, { signal })
export const getContractHubOptions = (signal: AbortSignal) => apiRequest<ContractHubOptions>('/api/v1/contracts/filter-options/', { signal })

const base = (scope: ContractScope) => 'hubContractId' in scope ? '/api/v1/contracts/' : 'projectId' in scope
  ? `/api/v1/projects/${scope.projectId}/contracts/`
  : `/api/v1/employees/${scope.employeeId}/contracts/`

export async function getContracts(scope: ContractScope, signal: AbortSignal): Promise<ContractCollection> {
  if ('projectId' in scope) return apiRequest<ContractCollection>(base(scope), { signal })
  const [items, capabilities] = await Promise.all([
    apiRequest<ContractRecord[]>(base(scope), { signal }),
    apiRequest<ContractCapabilities>(`${base(scope)}capabilities/`, { signal }),
  ])
  return { items, capabilities }
}
export const getContract = (scope: ContractScope, id: number, signal: AbortSignal) => apiRequest<ContractRecord>(`${base(scope)}${id}/`, { signal })
export const getContractOptions = (scope: ContractScope, signal: AbortSignal) => apiRequest<ContractOptions>('hubContractId' in scope ? `${base(scope)}${scope.hubContractId}/options/` : `${base(scope)}options/`, { signal })
const write = (method: 'POST' | 'PATCH', body: ContractWrite) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const createContract = (scope: ContractScope, body: ContractWrite) => apiRequest<ContractRecord>(base(scope), write('POST', body))
export const updateContract = (scope: ContractScope, id: number, body: ContractWrite) => apiRequest<ContractRecord>(`${base(scope)}${id}/`, write('PATCH', body))
export const deleteContract = (scope: ContractScope, id: number) => apiRequest<void>(`${base(scope)}${id}/`, { method: 'DELETE' })
export const syncEmployeeEndDate = (scope: ContractScope, id: number) => apiRequest<{ employee_id: number; end_date: string }>(`${base(scope)}${id}/sync-employee-end-date/`, { method: 'POST' })
