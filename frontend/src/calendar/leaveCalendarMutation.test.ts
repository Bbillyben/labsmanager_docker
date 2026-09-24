import { describe, expect, it } from 'vitest'
import type { CalendarEvent } from '../api/employees'
import { movedLeave, resizedLeave } from './leaveCalendarMutation'

const event: CalendarEvent = {
  id: 'leave:7', title: 'Leave', start: '2026-10-10T12:00:00', end: '2026-10-12T12:00:00',
  source: 'core', kind: 'leave', all_day: false, color: null, description: 'Family', display: 'auto',
  metadata: { leave_id: 7, leave_type_id: 3, start_date: '2026-10-10', start_period: 'MI', end_date: '2026-10-12', end_period: 'MI' },
}

describe('Calendar Leave date mutations', () => {
  it('moves both dates while retaining duration, periods and other fields', () => {
    expect(movedLeave(event, '2026-10-10T12:00:00', '2026-10-13T12:00:00')).toEqual({
      type_id: 3, start_date: '2026-10-13', start_period: 'MI', end_date: '2026-10-15', end_period: 'MI', comment: 'Family',
    })
  })

  it('resizes either edge using the change in FullCalendar exclusive endpoints', () => {
    expect(resizedLeave(event, '2026-10-10T12:00:00', '2026-10-09T12:00:00', '2026-10-12T12:00:00', '2026-10-12T12:00:00')).toMatchObject({ start_date: '2026-10-09', end_date: '2026-10-12', start_period: 'MI', end_period: 'MI' })
    expect(resizedLeave(event, '2026-10-10T12:00:00', '2026-10-10T12:00:00', '2026-10-12T12:00:00', '2026-10-15T12:00:00')).toMatchObject({ start_date: '2026-10-10', end_date: '2026-10-15', start_period: 'MI', end_period: 'MI' })
  })
})
