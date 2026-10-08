import type { DashboardEmployeeMovementsData } from '../api/dashboards'

export function isEmployeeMovements(data: unknown): data is DashboardEmployeeMovementsData {
  if (!data || typeof data !== 'object' || !('summary' in data) || !('items' in data)) return false
  const candidate = data as Partial<DashboardEmployeeMovementsData>
  return !!candidate.summary && typeof candidate.summary.count === 'number' &&
    typeof candidate.summary.arrivals_count === 'number' &&
    typeof candidate.summary.departures_count === 'number' && Array.isArray(candidate.items)
}
