import type { CalendarEvent } from '../api/employees'

export type ResourceVisibilityMode = 'period' | 'all' | 'today'
export type CalendarResource = { id: string; title: string }
export type CalendarRange = { from: string; to: string }

function localDay(value: string) {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function localToday() {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function dayBounds(date: string) {
  const start = localDay(date)
  const end = new Date(start)
  end.setDate(end.getDate() + 1)
  return { start: start.getTime(), end: end.getTime() }
}

function eventTime(value: string, allDay: boolean) {
  return allDay || /^\d{4}-\d{2}-\d{2}$/.test(value) ? localDay(value).getTime() : Date.parse(value)
}

export function eventIntersectsRange(event: CalendarEvent, start: number, end: number) {
  const eventStart = eventTime(event.start, event.all_day)
  if (!Number.isFinite(eventStart)) return false
  let eventEnd = event.end ? eventTime(event.end, event.all_day) : NaN
  if (!Number.isFinite(eventEnd) || eventEnd <= eventStart) {
    if (event.all_day) {
      const followingDay = localDay(event.start)
      followingDay.setDate(followingDay.getDate() + 1)
      eventEnd = followingDay.getTime()
    } else eventEnd = eventStart + 3_600_000
  }
  return eventStart < end && eventEnd > start
}

function resourceIds(value: unknown): string[] {
  const items = Array.isArray(value) ? value : [value]
  return items.filter((item): item is string | number => (typeof item === 'string' && item.trim() !== '') || (typeof item === 'number' && Number.isFinite(item)))
    .map(String)
}

/** Only explicit event associations count; globally displayed plugins do not. */
export function calendarEventResourceIds(event: CalendarEvent) {
  const metadata = event.metadata
  return [...new Set([
    ...resourceIds(metadata.employee_id), ...resourceIds(metadata.employee_ids),
    ...resourceIds(metadata.resource_id), ...resourceIds(metadata.resource_ids),
    ...resourceIds(metadata.resourceId), ...resourceIds(metadata.resourceIds),
  ])]
}

export function visibleCalendarResources(resources: CalendarResource[], events: CalendarEvent[], mode: ResourceVisibilityMode, range: CalendarRange, today = localToday()) {
  if (mode === 'all') return resources
  const bounds = mode === 'today' ? dayBounds(today) : { start: dayBounds(range.from).start, end: dayBounds(range.to).end }
  const active = new Set<string>()
  for (const event of events) {
    if (!eventIntersectsRange(event, bounds.start, bounds.end)) continue
    for (const id of calendarEventResourceIds(event)) active.add(id)
  }
  return resources.filter((resource) => active.has(resource.id))
}
