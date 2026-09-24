import type { CalendarEvent, LeaveWrite } from '../api/employees'

function shiftDate(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

function dayDifference(before: string, after: string) {
  return (Date.parse(`${after.slice(0, 10)}T00:00:00Z`) - Date.parse(`${before.slice(0, 10)}T00:00:00Z`)) / 86_400_000
}

export function leaveWriteFromCalendarEvent(event: CalendarEvent): LeaveWrite {
  const metadata = event.metadata
  return {
    type_id: Number(metadata.leave_type_id),
    start_date: String(metadata.start_date),
    start_period: metadata.start_period as LeaveWrite['start_period'],
    end_date: String(metadata.end_date),
    end_period: metadata.end_period as LeaveWrite['end_period'],
    comment: event.description ?? '',
  }
}

export function movedLeave(event: CalendarEvent, oldStart: string, newStart: string): LeaveWrite {
  const original = leaveWriteFromCalendarEvent(event)
  const days = dayDifference(oldStart, newStart)
  return { ...original, start_date: shiftDate(original.start_date, days), end_date: shiftDate(original.end_date, days) }
}

export function resizedLeave(event: CalendarEvent, oldStart: string, newStart: string, oldEnd: string, newEnd: string): LeaveWrite {
  const original = leaveWriteFromCalendarEvent(event)
  return {
    ...original,
    start_date: shiftDate(original.start_date, dayDifference(oldStart, newStart)),
    end_date: shiftDate(original.end_date, dayDifference(oldEnd, newEnd)),
  }
}
