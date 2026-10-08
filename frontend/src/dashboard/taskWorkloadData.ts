import type { DashboardTaskWorkloadData } from '../api/dashboards'

export function isTaskWorkload(data: unknown): data is DashboardTaskWorkloadData {
  if (!data || typeof data !== 'object' || !('summary' in data) || !('items' in data)) return false
  const candidate = data as Partial<DashboardTaskWorkloadData>
  return !!candidate.summary && typeof candidate.summary.count === 'number' &&
    typeof candidate.summary.overdue_count === 'number' &&
    typeof candidate.summary.due_soon_count === 'number' && Array.isArray(candidate.items)
}
