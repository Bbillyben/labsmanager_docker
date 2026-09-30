import { apiRequest } from './client'
import type { EmployeeContract } from './employees'

export type ContractScope = { projectId: string; employeeId?: never } | { employeeId: string; projectId?: never }
export type ContractCapabilities = { can_add: boolean; can_change: boolean; can_delete: boolean }
export type EmployeeEndDateSyncOffer = { employee_id: number; current_end_date: string | null; proposed_end_date: string; can_update: boolean }
export type ContractRecord = EmployeeContract & {
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

const base = (scope: ContractScope) => 'projectId' in scope
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
export const getContractOptions = (scope: ContractScope, signal: AbortSignal) => apiRequest<ContractOptions>(`${base(scope)}options/`, { signal })
const write = (method: 'POST' | 'PATCH', body: ContractWrite) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const createContract = (scope: ContractScope, body: ContractWrite) => apiRequest<ContractRecord>(base(scope), write('POST', body))
export const updateContract = (scope: ContractScope, id: number, body: ContractWrite) => apiRequest<ContractRecord>(`${base(scope)}${id}/`, write('PATCH', body))
export const deleteContract = (scope: ContractScope, id: number) => apiRequest<void>(`${base(scope)}${id}/`, { method: 'DELETE' })
export const syncEmployeeEndDate = (scope: ContractScope, id: number) => apiRequest<{ employee_id: number; end_date: string }>(`${base(scope)}${id}/sync-employee-end-date/`, { method: 'POST' })
