import { describe, expect, it } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { toFullCalendarEvent } from './fullCalendarAdapter'

const event: CalendarEvent = {
  id: 'leave:7', title: 'Congés payés', start: '2026-09-10T12:00:00', end: '2026-09-12T12:00:00',
  source: 'core', kind: 'leave', all_day: false, color: '#336699', description: 'Famille', display: 'auto',
  metadata: { leave_id: 7, start_period: 'MI', end_period: 'MI' },
}

describe('FullCalendar adapter', () => {
  it('maps the calendar contract without splitting a multi-day event', () => {
    expect(toFullCalendarEvent(event)).toEqual({
      id: 'leave:7', title: 'Congés payés', start: '2026-09-10T12:00:00', end: '2026-09-12T12:00:00',
      allDay: false, color: '#336699', display: 'auto', interactive: true, editable: false,
      extendedProps: { description: 'Famille', source: 'core', kind: 'leave', metadata: { leave_id: 7, start_period: 'MI', end_period: 'MI' } },
    })
  })

  it('permits editing only core Leave events when the business capability allows it', () => {
    expect(toFullCalendarEvent(event, true).editable).toBe(true)
    expect(toFullCalendarEvent(event, false).editable).toBe(false)
    expect(toFullCalendarEvent({ ...event, source: 'plugin' }, true).editable).toBe(false)
    expect(toFullCalendarEvent({ ...event, kind: 'holiday' }, true).editable).toBe(false)
  })

  it('keeps plugin background events native and non-interactive', () => {
    const result = toFullCalendarEvent({ ...event, id: 'plugin:1', kind: 'school_holiday', source: 'frenchholliday', display: 'background', all_day: true })
    expect(result).toMatchObject({ display: 'background', allDay: true, interactive: false })
    expect(result.extendedProps).toMatchObject({ kind: 'school_holiday', source: 'frenchholliday' })
  })
})
