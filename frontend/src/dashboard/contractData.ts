import type { DashboardContractData } from '../api/dashboards'

export function isContractData(data: unknown): data is DashboardContractData {
  if (!data || typeof data !== 'object' || !('summary' in data) || !('items' in data)) return false
  const candidate = data as Partial<DashboardContractData>
  return !!candidate.summary && typeof candidate.summary.count === 'number' &&
    typeof candidate.summary.ending_soon_count === 'number' &&
    typeof candidate.summary.stale_count === 'number' && Array.isArray(candidate.items)
}

export function hasContracts(data: unknown): data is { contracts: DashboardContractData } {
  return !!data && typeof data === 'object' && 'contracts' in data && isContractData(data.contracts)
}
