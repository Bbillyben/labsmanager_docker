import type { EventInput } from '@fullcalendar/react';
import type { CalendarEvent } from '../api/employees';
import { calendarEventResourceIds } from './resourceVisibility';

/** Extra event fields consumed by LabsManager calendar interactions. */
export type LabsManagerEventProps = {
  description: string | null;
  source: string;
  kind: string;
  metadata: Record<string, unknown>;
};

/** Convert one API event into FullCalendar event input. */
export function toFullCalendarEvent(event: CalendarEvent, canChange = false): EventInput {
  const leaveId = Number(event.metadata.leave_id);
  const isLeave =
    event.source === 'core' &&
    event.kind === 'leave' &&
    Number.isInteger(leaveId) &&
    leaveId > 0 &&
    event.display !== 'background';
  const isMaintenance = event.source === 'core' && event.kind === 'equipment-maintenance';
  const resourceIds = calendarEventResourceIds(event);
  return {
    id: event.id,
    title: event.title,
    start: event.start,
    end: event.end ?? undefined,
    allDay: event.all_day,
    color: event.color ?? undefined,
    display: event.display || 'auto',
    interactive: isLeave || isMaintenance,
    editable: isLeave && canChange,
    resourceId: resourceIds.length === 1 ? resourceIds[0] : undefined,
    resourceIds: resourceIds.length > 1 ? resourceIds : undefined,
    extendedProps: {
      description: event.description,
      source: event.source,
      kind: event.kind,
      metadata: event.metadata,
    } satisfies LabsManagerEventProps,
  };
}

/** Convert a collection of API events for FullCalendar rendering. */
export function toFullCalendarEvents(events: CalendarEvent[], canChange = false): EventInput[] {
  return events.map((event) => toFullCalendarEvent(event, canChange));
}
