import type { DashboardOverviewData } from '../api/dashboards'

export function isOverview(data: unknown): data is DashboardOverviewData {
  if (!data || typeof data !== 'object' || !('summary' in data) || !('items' in data)) return false
  const candidate = data as Partial<DashboardOverviewData>
  return !!candidate.summary && typeof candidate.summary.amount === 'number' &&
    typeof candidate.summary.spent === 'number' && typeof candidate.summary.count === 'number' &&
    Array.isArray(candidate.items)
}

export function hasOverview(data: unknown): data is { overview: DashboardOverviewData } {
  return !!data && typeof data === 'object' && 'overview' in data && isOverview(data.overview)
}
