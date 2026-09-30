import { describe, expect, it } from 'vitest'
import { leaveDatesFromSelection } from './leaveSelection'

describe('FullCalendar all-day selection for Leave', () => {
  it('converts one selected day to an inclusive full day', () => {
    expect(leaveDatesFromSelection('2026-10-06', '2026-10-07')).toEqual({ start_date: '2026-10-06', end_date: '2026-10-06' })
  })
  it('converts a multi-day exclusive end without adding a day', () => {
    expect(leaveDatesFromSelection('2026-10-06', '2026-10-11')).toEqual({ start_date: '2026-10-06', end_date: '2026-10-10' })
  })
  it('keeps the selected day when a timed range ends during that day', () => {
    expect(leaveDatesFromSelection('2026-10-06T12:00:00+02:00', '2026-10-06T18:00:00+02:00', false)).toEqual({ start_date: '2026-10-06', end_date: '2026-10-06' })
  })
  it('excludes the last day when a timed range ends at midnight', () => {
    expect(leaveDatesFromSelection('2026-10-06T12:00:00+02:00', '2026-10-09T00:00:00+02:00', false)).toEqual({ start_date: '2026-10-06', end_date: '2026-10-08' })
  })
})
