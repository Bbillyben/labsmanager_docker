import type { CalendarEvent, LeaveWrite } from '../api/employees'
import { SharedCalendar } from '../calendar/SharedCalendar'
import type { ProjectCalendarScope } from './projectCalendarScopes'

export function EmployeeCalendar({ anchor, events, onOpen, onCreate, onChangeDates, canCreate, canChange, canChangeEvent, projectScope, projectEmployeeNames }: { anchor: Date; events: CalendarEvent[]; onOpen: (event: CalendarEvent) => void; onCreate: (dates: { start_date: string; end_date: string }) => void; onChangeDates: (event: CalendarEvent, write: LeaveWrite) => Promise<void>; canCreate: boolean; canChange: boolean; canChangeEvent?: (event: CalendarEvent) => boolean; projectScope: ProjectCalendarScope; projectEmployeeNames?: ReadonlyMap<number, string> }) {
  return <SharedCalendar anchor={anchor} events={events} scope={projectScope} viewMode="calendar" employeeNames={projectEmployeeNames} onOpen={onOpen} onCreate={(dates) => onCreate(dates)} onChangeDates={onChangeDates} canCreate={canCreate} canChange={canChange} canChangeEvent={canChangeEvent} />
}
