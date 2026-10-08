import type { DashboardDeadlineData } from '../api/dashboards'

export function isDeadline(data: unknown): data is DashboardDeadlineData {
  if (!data || typeof data !== 'object' || !('summary' in data) || !('items' in data)) return false
  const candidate = data as Partial<DashboardDeadlineData>
  return !!candidate.summary && typeof candidate.summary.count === 'number' &&
    typeof candidate.summary.overdue_count === 'number' &&
    typeof candidate.summary.due_soon_count === 'number' && Array.isArray(candidate.items)
}

export function hasDeadline(data: unknown): data is { deadline: DashboardDeadlineData } {
  return !!data && typeof data === 'object' && 'deadline' in data && isDeadline(data.deadline)
}
