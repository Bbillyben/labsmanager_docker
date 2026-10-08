import type { DashboardTimelineData } from '../api/dashboards'

export function isTimeline(value: unknown): value is DashboardTimelineData {
  return !!value && typeof value === 'object' && Array.isArray((value as DashboardTimelineData).events)
}

export function timelineDays(start: string, end: string) {
  const days: string[] = []
  const cursor = new Date(`${start}T00:00:00Z`)
  const final = new Date(`${end}T00:00:00Z`)
  while (cursor <= final && days.length < 70) {
    days.push(cursor.toISOString().slice(0, 10))
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return days
}
