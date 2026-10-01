import FullCalendar, { type EventClickInfo, type EventDisplayInfo } from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import timelinePlugin from '@fullcalendar/react-scheduler/timeline'
import interactionPlugin from '@fullcalendar/react/interaction'
import enGbLocale from '@fullcalendar/react/locales/en-gb'
import frLocale from '@fullcalendar/react/locales/fr'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { useMemo, useRef } from 'react'
import type { CalendarEvent, LeaveWrite } from '../api/employees'
import { toFullCalendarEvent, type LabsManagerEventProps } from '../calendar/fullCalendarAdapter'
import { movedLeave, resizedLeave } from '../calendar/leaveCalendarMutation'
import { leaveDatesFromSelection } from '../calendar/leaveSelection'
import { halfDayLabel } from '../calendar/halfDayPresentation'
import { useTranslation } from '../i18n/i18n'
import styles from './EmployeeLeaves.module.css'
import { projectCalendarScopes, projectDayGridViews, type ProjectCalendarScope } from './projectCalendarScopes'

export function EmployeeCalendar({ anchor, events, onOpen, onCreate, onChangeDates, canCreate, canChange, canChangeEvent, projectScope, projectEmployeeNames }: { anchor: Date; events: CalendarEvent[]; onOpen: (event: CalendarEvent) => void; onCreate: (dates: { start_date: string; end_date: string }) => void; onChangeDates: (event: CalendarEvent, write: LeaveWrite) => Promise<void>; canCreate: boolean; canChange: boolean; canChangeEvent?: (event: CalendarEvent) => boolean; projectScope: ProjectCalendarScope; projectEmployeeNames?: ReadonlyMap<number, string> }) {
  const { language, t } = useTranslation()
  const mappedEvents = useMemo(() => events.map((event) => toFullCalendarEvent(event, canChange && (canChangeEvent?.(event) ?? true))), [events, canChange, canChangeEvent])
  const suppressClick = useRef(false)
  const byId = new Map(events.map((event) => [event.id, event]))
  const handleClick = (info: EventClickInfo) => {
    if (suppressClick.current) return
    const event = byId.get(info.event.id)
    const props = info.event.extendedProps as LabsManagerEventProps
    if (event && props.source === 'core' && props.kind === 'leave') onOpen(event)
  }
  const stopGesture = () => { window.setTimeout(() => { suppressClick.current = false }, 250) }
  const applyGesture = async (id: string, write: LeaveWrite, revert: () => void) => {
    const source = byId.get(id)
    if (!source || !canChange || (canChangeEvent && !canChangeEvent(source)) || source.source !== 'core' || source.kind !== 'leave') { revert(); return }
    try { await onChangeDates(source, write) } catch { revert() }
  }
  const renderEvent = (info: EventDisplayInfo) => {
    const props = info.event.extendedProps as LabsManagerEventProps
    const period = props.kind === 'leave' ? halfDayLabel(props.metadata, t) : ''
    const isLeave = props.source === 'core' && props.kind === 'leave'
    const employeeName = isLeave ? projectEmployeeNames?.get(Number(props.metadata.employee_id)) : undefined
    const title = employeeName ? `${employeeName} — ${info.event.title}` : info.event.title
    const content = <><span>{title}</span>{period && <small>{period}</small>}</>
    if (isLeave) return <button aria-label={t('leaves.open', { name: title })} className={styles.fullCalendarEventButton} onClick={(event) => {
      event.stopPropagation()
      if (suppressClick.current) return
      const sourceEvent = byId.get(info.event.id)
      if (sourceEvent) onOpen(sourceEvent)
    }} type="button">{content}</button>
    return <span className={styles.fullCalendarEvent}>{content}</span>
  }
  const mountEvent = (info: EventDisplayInfo & { el: HTMLElement }) => {
    const props = info.event.extendedProps as LabsManagerEventProps
    const tooltip = props.description || info.event.title
    if (tooltip) info.el.setAttribute('title', tooltip)
  }

  return <div aria-label={t('leaves.calendarLabel')} className={`${styles.fullCalendar} ${styles.fullCalendarScoped}`} role="region">
    <FullCalendar
      dayMaxEvents={false}
      dayMaxEventRows={false}
      editable={canChange}
      eventClick={handleClick}
      eventContent={renderEvent}
      eventDidMount={mountEvent}
      eventDragStart={() => { suppressClick.current = true }}
      eventDragStop={stopGesture}
      eventDrop={(info) => {
        const source = byId.get(info.event.id)
        if (!source || !info.oldEvent.startStr || !info.event.startStr) { info.revert(); return }
        void applyGesture(info.event.id, movedLeave(source, info.oldEvent.startStr, info.event.startStr), info.revert)
      }}
      eventResizableFromStart
      eventResizeStart={() => { suppressClick.current = true }}
      eventResizeStop={stopGesture}
      eventResize={(info) => {
        const source = byId.get(info.event.id)
        if (!source || !info.oldEvent.startStr || !info.event.startStr || !info.oldEvent.endStr || !info.event.endStr) { info.revert(); return }
        void applyGesture(info.event.id, resizedLeave(source, info.oldEvent.startStr, info.event.startStr, info.oldEvent.endStr, info.event.endStr), info.revert)
      }}
      events={mappedEvents}
      firstDay={1}
      fixedWeekCount={false}
      headerToolbar={false}
      initialDate={anchor}
      initialView={projectCalendarScopes[projectScope].calendarView}
      key={`${projectScope}:${anchor.getFullYear()}:${anchor.getMonth()}:${anchor.getDate()}`}
      locale={language.startsWith('fr') ? frLocale : enGbLocale}
      plugins={[dayGridPlugin, timelinePlugin, interactionPlugin, classicThemePlugin]}
      views={projectDayGridViews}
      selectable={canCreate}
      select={(selection) => onCreate(leaveDatesFromSelection(selection.startStr, selection.endStr, selection.allDay))}
      schedulerLicenseKey="AGPL-My-Frontend-And-Backend-Are-Open-Source"
    />
  </div>
}
