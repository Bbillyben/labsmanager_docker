import FullCalendar, { type EventClickInfo, type EventDisplayInfo } from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import enGbLocale from '@fullcalendar/react/locales/en-gb'
import frLocale from '@fullcalendar/react/locales/fr'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { useMemo, useRef } from 'react'
import type { CalendarEvent, LeaveWrite } from '../api/employees'
import { toFullCalendarEvents, type LabsManagerEventProps } from '../calendar/fullCalendarAdapter'
import { movedLeave, resizedLeave } from '../calendar/leaveCalendarMutation'
import { leaveDatesFromSelection } from '../calendar/leaveSelection'
import { halfDayLabel } from '../calendar/halfDayPresentation'
import { useTranslation } from '../i18n/i18n'
import styles from './EmployeeLeaves.module.css'

export type EmployeeCalendarView = 'month' | 'year' | 'fiveYears'

export function EmployeeCalendar({ anchor, events, onOpen, onCreate, onChangeDates, canCreate, canChange, view }: { anchor: Date; events: CalendarEvent[]; onOpen: (event: CalendarEvent) => void; onCreate: (dates: { start_date: string; end_date: string }) => void; onChangeDates: (event: CalendarEvent, write: LeaveWrite) => Promise<void>; canCreate: boolean; canChange: boolean; view: EmployeeCalendarView }) {
  const { language, t } = useTranslation()
  const mappedEvents = useMemo(() => toFullCalendarEvents(events, canChange), [events, canChange])
  const suppressClick = useRef(false)
  if (view === 'fiveYears') return <FiveYearCalendar anchor={anchor} events={events} onOpen={onOpen} />

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
    if (!source || !canChange || source.source !== 'core' || source.kind !== 'leave') { revert(); return }
    try { await onChangeDates(source, write) } catch { revert() }
  }
  const renderEvent = (info: EventDisplayInfo) => {
    const props = info.event.extendedProps as LabsManagerEventProps
    const period = props.kind === 'leave' ? halfDayLabel(props.metadata, t) : ''
    const content = <><span>{info.event.title}</span>{period && <small>{period}</small>}</>
    if (props.source === 'core' && props.kind === 'leave') return <button aria-label={t('leaves.open', { name: info.event.title })} className={styles.fullCalendarEventButton} onClick={(event) => {
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

  return <div aria-label={t('leaves.calendarLabel')} className={`${styles.fullCalendar} ${view === 'year' ? styles.fullCalendarYear : styles.fullCalendarMonth}`} role="region">
    <FullCalendar
      dayMaxEvents={3}
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
      initialView={view === 'month' ? 'dayGridMonth' : 'dayGridYear'}
      key={`${view}:${anchor.getFullYear()}:${anchor.getMonth()}`}
      locale={language.startsWith('fr') ? frLocale : enGbLocale}
      plugins={[dayGridPlugin, interactionPlugin, classicThemePlugin]}
      selectable={canCreate}
      select={(selection) => { if (selection.allDay) onCreate(leaveDatesFromSelection(selection.startStr, selection.endStr)) }}
    />
  </div>
}

function FiveYearCalendar({ anchor, events, onOpen }: { anchor: Date; events: CalendarEvent[]; onOpen: (event: CalendarEvent) => void }) {
  const { language, t } = useTranslation()
  const years = Array.from({ length: 5 }, (_, index) => anchor.getFullYear() - 2 + index)
  return <div aria-label={t('leaves.calendarLabel')} className={styles.compactCalendar} role="region">
    {years.map((year) => <section className={styles.compactYear} key={year}>
      <h2>{year}</h2>
      <div className={styles.months}>{Array.from({ length: 12 }, (_, month) => <MonthSummary events={events} key={month} language={language} month={month} onOpen={onOpen} year={year} />)}</div>
    </section>)}
  </div>
}

function MonthSummary({ events, language, month, onOpen, year }: { events: CalendarEvent[]; language: string; month: number; onOpen: (event: CalendarEvent) => void; year: number }) {
  const monthEvents = events.filter((event) => event.display !== 'background' && overlapsMonth(event, year, month))
  return <section className={styles.monthSummary}>
    <h3>{new Intl.DateTimeFormat(language, { month: 'short' }).format(new Date(year, month, 1))}<span>{monthEvents.length || ''}</span></h3>
    <div>{monthEvents.map((event) => <CompactEvent event={event} key={event.id} onOpen={onOpen} />)}</div>
  </section>
}

function CompactEvent({ event, onOpen }: { event: CalendarEvent; onOpen: (event: CalendarEvent) => void }) {
  const { language, t } = useTranslation()
  const style = event.color ? { borderInlineStartColor: event.color } : undefined
  const dates = calendarEventDateLabel(event, language)
  if (event.kind !== 'leave') return <span className={styles.pluginEvent} style={style} title={event.description ?? t('leaves.pluginEvent')}>{event.title || event.description || t('leaves.pluginEvent')} · {dates}</span>
  const period = halfDayLabel(event.metadata, t)
  return <button aria-label={t('leaves.open', { name: event.title })} className={styles.event} onClick={() => onOpen(event)} style={style} type="button"><span>{event.title}</span><small>{dates}{period ? ` · ${period}` : ''}</small></button>
}

function eventTime(value: string) { return new Date(value.length === 10 ? `${value}T00:00:00Z` : value).getTime() }
function overlapsMonth(event: CalendarEvent, year: number, month: number) { const start = Date.UTC(year, month, 1); const end = Date.UTC(year, month + 1, 1); return eventTime(event.start) < end && eventTime(event.end ?? event.start) > start }

function calendarEventDateLabel(event: CalendarEvent, language: string) {
  const start = new Date(event.start.length === 10 ? `${event.start}T00:00:00Z` : event.start)
  const end = event.end ? new Date(event.end.length === 10 ? `${event.end}T00:00:00Z` : event.end) : start
  if (event.all_day && event.end) end.setUTCDate(end.getUTCDate() - 1)
  const format = new Intl.DateTimeFormat(language, { dateStyle: 'short', timeZone: 'UTC' })
  const startLabel = format.format(start)
  const endLabel = format.format(end)
  return startLabel === endLabel ? startLabel : `${startLabel} → ${endLabel}`
}
