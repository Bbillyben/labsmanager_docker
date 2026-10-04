import type { EventInput } from '@fullcalendar/react'
import type { CalendarEvent } from '../api/employees'
import { calendarEventResourceIds } from './resourceVisibility'

export type LabsManagerEventProps = {
  description: string | null
  source: string
  kind: string
  metadata: Record<string, unknown>
}

export function toFullCalendarEvent(event: CalendarEvent, canChange = false): EventInput {
  const leaveId = Number(event.metadata.leave_id)
  const isLeave = event.source === 'core' && event.kind === 'leave' && Number.isInteger(leaveId) && leaveId > 0 && event.display !== 'background'
  const resourceIds = calendarEventResourceIds(event)
  return {
    id: event.id,
    title: event.title,
    start: event.start,
    end: event.end ?? undefined,
    allDay: event.all_day,
    color: event.color ?? undefined,
    display: event.display || 'auto',
    interactive: isLeave,
    editable: isLeave && canChange,
    resourceId: resourceIds.length === 1 ? resourceIds[0] : undefined,
    resourceIds: resourceIds.length > 1 ? resourceIds : undefined,
    extendedProps: {
      description: event.description,
      source: event.source,
      kind: event.kind,
      metadata: event.metadata,
    } satisfies LabsManagerEventProps,
  }
}

export function toFullCalendarEvents(events: CalendarEvent[], canChange = false): EventInput[] {
  return events.map((event) => toFullCalendarEvent(event, canChange))
}
