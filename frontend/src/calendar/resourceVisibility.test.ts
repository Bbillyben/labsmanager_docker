import { describe, expect, it } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { calendarEventResourceIds, eventIntersectsRange, visibleCalendarResources } from './resourceVisibility'

const resources = [{ id: '1', title: 'Ada' }, { id: '2', title: 'Bea' }, { id: '3', title: 'Cy' }]
const range = { from: '2026-10-01', to: '2026-10-31' }
const leave = (id: string, start: string, end: string | null, metadata: Record<string, unknown> = { employee_id: id }): CalendarEvent => ({
  id: `event:${id}:${start}`, title: 'Leave', start, end, source: 'core', kind: 'leave', all_day: true, color: null, description: null, display: 'auto', metadata,
})

describe('Calendar Resource visibility', () => {
  it('keeps period events and both kinds of overlap, with exclusive all-day end', () => {
    const events = [
      leave('1', '2026-10-10', '2026-10-12'),
      leave('2', '2026-09-28', '2026-10-02'),
      leave('3', '2026-10-31', '2026-11-03'),
    ]
    expect(visibleCalendarResources(resources, events, 'period', range)).toEqual(resources)
    expect(visibleCalendarResources(resources, [leave('1', '2026-09-30', '2026-10-01')], 'period', range)).toEqual([])
    expect(visibleCalendarResources(resources, [leave('1', '2026-11-01', '2026-11-02')], 'period', range)).toEqual([])
  })

  it('treats a no-end all-day event as one local day and a timed event as one hour', () => {
    const allDay = leave('1', '2026-10-31', null)
    const timed = { ...leave('2', '2026-10-31T23:30:00+02:00', null), all_day: false }
    const start = new Date(2026, 9, 31).getTime()
    const end = new Date(2026, 10, 1).getTime()
    expect(eventIntersectsRange(allDay, start, end)).toBe(true)
    expect(eventIntersectsRange(timed, start, end)).toBe(true)
  })

  it('all shows only the already supplied resource dataset', () => {
    expect(visibleCalendarResources(resources.slice(0, 2), [], 'all', range)).toEqual(resources.slice(0, 2))
  })

  it('today uses the real local day independently of the visible period', () => {
    const pastRange = { from: '2024-01-01', to: '2024-12-31' }
    const events = [leave('1', '2026-10-03', '2026-10-04'), leave('2', '2026-10-04', '2026-10-05')]
    expect(visibleCalendarResources(resources, events, 'today', pastRange, '2026-10-03')).toEqual([resources[0]])
  })

  it('counts scoped background events but not global background events', () => {
    const scoped = { ...leave('2', '2026-10-10', '2026-10-15'), display: 'background', source: 'plugin', kind: 'holiday' }
    const global = { ...scoped, id: 'global', metadata: {} }
    expect(visibleCalendarResources(resources, [scoped, global], 'period', range)).toEqual([resources[1]])
    expect(visibleCalendarResources(resources, [global], 'period', range)).toEqual([])
  })

  it('includes every explicitly associated resource for multi-resource events', () => {
    const event = leave('multi', '2026-10-10', '2026-10-12', { resource_ids: [1, '3'] })
    expect(calendarEventResourceIds(event)).toEqual(['1', '3'])
    expect(visibleCalendarResources(resources, [event], 'period', range)).toEqual([resources[0], resources[2]])
  })
})
