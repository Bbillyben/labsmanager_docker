import FullCalendar, { type EventClickInfo, type EventDisplayInfo } from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import enGbLocale from '@fullcalendar/react/locales/en-gb'
import frLocale from '@fullcalendar/react/locales/fr'
import timelinePlugin from '@fullcalendar/react-scheduler/timeline'
import resourceTimelinePlugin from '@fullcalendar/react-scheduler/resource-timeline'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/classic/theme.css'
import '@fullcalendar/react/themes/classic/palette.css'
import { useMemo, useRef, useState } from 'react'
import type { CalendarEvent, LeaveWrite } from '../api/employees'
import { useTranslation } from '../i18n/i18n'
import { projectCalendarRange, projectCalendarViewDefinition, projectDayGridViews, projectResourceViews, type CalendarViewMode, type ProjectCalendarScope } from '../pages/projectCalendarScopes'
import styles from '../pages/EmployeeLeaves.module.css'
import { toFullCalendarEvent, type LabsManagerEventProps } from './fullCalendarAdapter'
import { halfDayLabel } from './halfDayPresentation'
import { movedLeave, resizedLeave } from './leaveCalendarMutation'
import { leaveDatesFromSelection } from './leaveSelection'
import { calendarEventResourceIds, visibleCalendarResources, type CalendarResource, type ResourceVisibilityMode } from './resourceVisibility'

export type { CalendarViewMode } from '../pages/projectCalendarScopes'
export type { CalendarResource, ResourceVisibilityMode } from './resourceVisibility'
type Dates = { start_date: string; end_date: string }
const emptyResources: CalendarResource[] = []

export function SharedCalendar({ anchor, scope, viewMode, events, resources = emptyResources, todayEvents, resourceVisibilityMode, onResourceVisibilityModeChange, employeeNames, canCreate = false, canChange = false, canChangeEvent, canCreateResource, onOpen, onCreate, onChangeDates, print = false, onReady }: {
  anchor: Date
  scope: ProjectCalendarScope
  viewMode: CalendarViewMode
  events: CalendarEvent[]
  resources?: CalendarResource[]
  todayEvents?: CalendarEvent[]
  resourceVisibilityMode?: ResourceVisibilityMode
  onResourceVisibilityModeChange?: (mode: ResourceVisibilityMode) => void
  employeeNames?: ReadonlyMap<number, string>
  canCreate?: boolean
  canChange?: boolean
  canChangeEvent?: (event: CalendarEvent) => boolean
  canCreateResource?: (resourceId: string) => boolean
  onOpen?: (event: CalendarEvent) => void
  onCreate?: (dates: Dates, resourceId?: string) => void
  onChangeDates?: (event: CalendarEvent, write: LeaveWrite) => Promise<void>
  print?: boolean
  onReady?: () => void
}) {
  const { language, t } = useTranslation()
  const definition = projectCalendarViewDefinition(scope, viewMode)
  const [localVisibilityMode, setLocalVisibilityMode] = useState<ResourceVisibilityMode>('period')
  const visibilityMode = resourceVisibilityMode ?? localVisibilityMode
  const visibleResources = useMemo(() => viewMode === 'resources'
    ? visibleCalendarResources(resources, visibilityMode === 'today' ? todayEvents ?? [] : events, visibilityMode, projectCalendarRange(scope, anchor))
    : emptyResources, [resources, visibilityMode, todayEvents, events, scope, anchor, viewMode])
  const suppressClick = useRef(false)
  const byId = useMemo(() => new Map(events.map((event) => [event.id, event])), [events])
  const mappedEvents = useMemo(() => {
    const visibleIds = new Set(visibleResources.map((resource) => resource.id))
    return events.flatMap((event) => {
      const mapped = toFullCalendarEvent(event, !print && canChange && (canChangeEvent?.(event) ?? true))
      const associated = calendarEventResourceIds(event)
      const assigned = associated.filter((id) => visibleIds.has(id))
      if (viewMode === 'resources' && associated.length && !assigned.length) return []
      if (viewMode === 'resources' && !associated.length && !visibleResources.length) return []
      const positioned = viewMode === 'resources'
        ? { ...mapped, resourceId: assigned.length === 1 ? assigned[0] : undefined, resourceIds: assigned.length > 1 ? assigned : associated.length ? undefined : visibleResources.map((resource) => resource.id) }
        : mapped
      return [print ? { ...positioned, interactive: false, editable: false } : positioned]
    })
  }, [events, print, canChange, canChangeEvent, viewMode, visibleResources])
  const openEvent = (event: CalendarEvent) => {
    if (!print && !suppressClick.current && event.source === 'core' && event.kind === 'leave') onOpen?.(event)
  }
  const applyGesture = async (id: string, write: LeaveWrite, revert: () => void) => {
    const source = byId.get(id)
    if (!source || !onChangeDates || !canChange || (canChangeEvent && !canChangeEvent(source)) || source.source !== 'core' || source.kind !== 'leave') { revert(); return }
    try { await onChangeDates(source, write) } catch { revert() }
  }
  const renderEvent = (info: EventDisplayInfo) => {
    const event = byId.get(info.event.id)
    const props = info.event.extendedProps as LabsManagerEventProps
    const isLeave = event?.source === 'core' && event.kind === 'leave'
    const period = isLeave ? halfDayLabel(props.metadata, t) : ''
    const employee = isLeave && viewMode === 'calendar' ? employeeNames?.get(Number(props.metadata.employee_id)) : null
    const title = employee ? `${employee} — ${info.event.title}` : info.event.title
    const content = <><span>{title}</span>{period && <small>{period}</small>}</>
    if (isLeave && !print) return <button aria-label={t('leaves.open', { name: title })} className={styles.fullCalendarEventButton} onClick={(click) => { click.stopPropagation(); openEvent(event) }} type="button">{content}</button>
    return <span className={styles.fullCalendarEvent}>{content}</span>
  }
  return <div aria-label={t(viewMode === 'resources' ? 'projectCalendar.resources' : 'leaves.calendarLabel')} className={`${styles.fullCalendar} ${styles.fullCalendarScoped} ${print ? styles.fullCalendarPrint : ''}`} role="region" data-calendar-view={definition.key} data-calendar-mode={viewMode} data-resource-visibility={viewMode === 'resources' ? visibilityMode : undefined}>
    {viewMode === 'resources' && !print && <label className={styles.resourceVisibility}>{t('projectCalendar.resources')}
      <select value={visibilityMode} onChange={(event) => { const next = event.target.value as ResourceVisibilityMode; setLocalVisibilityMode(next); onResourceVisibilityModeChange?.(next) }}>
        <option value="period">{t('projectCalendar.resourceVisibilityPeriod')}</option>
        <option value="all">{t('projectCalendar.resourceVisibilityAll')}</option>
        <option value="today">{t('projectCalendar.resourceVisibilityToday')}</option>
      </select>
    </label>}
    <FullCalendar
      dayMaxEvents={false}
      dayMaxEventRows={false}
      editable={!print && canChange}
      eventClick={(info: EventClickInfo) => { const event = byId.get(info.event.id); if (event) openEvent(event) }}
      eventContent={renderEvent}
      eventDidMount={(info) => { const props = info.event.extendedProps as LabsManagerEventProps; const tooltip = props.description || info.event.title; if (tooltip) info.el.setAttribute('title', tooltip) }}
      eventDragStart={() => { suppressClick.current = true }}
      eventDragStop={() => { window.setTimeout(() => { suppressClick.current = false }, 250) }}
      eventDrop={(info) => { const event = byId.get(info.event.id); if (!event || !info.oldEvent.startStr || !info.event.startStr) { info.revert(); return }; void applyGesture(info.event.id, movedLeave(event, info.oldEvent.startStr, info.event.startStr), info.revert) }}
      eventResizableFromStart={!print}
      eventResizeStart={() => { suppressClick.current = true }}
      eventResizeStop={() => { window.setTimeout(() => { suppressClick.current = false }, 250) }}
      eventResize={(info) => { const event = byId.get(info.event.id); if (!event || !info.oldEvent.startStr || !info.event.startStr || !info.oldEvent.endStr || !info.event.endStr) { info.revert(); return }; void applyGesture(info.event.id, resizedLeave(event, info.oldEvent.startStr, info.event.startStr, info.oldEvent.endStr, info.event.endStr), info.revert) }}
      events={mappedEvents}
      firstDay={1}
      fixedWeekCount={false}
      headerToolbar={false}
      height={print ? 'auto' : undefined}
      contentHeight={print ? 'auto' : undefined}
      initialDate={anchor}
      initialView={definition.key}
      key={`${definition.key}:${anchor.getFullYear()}:${anchor.getMonth()}:${anchor.getDate()}:${print}`}
      locale={language.startsWith('fr') ? frLocale : enGbLocale}
      plugins={[dayGridPlugin, timelinePlugin, resourceTimelinePlugin, interactionPlugin, classicThemePlugin]}
      views={viewMode === 'resources' ? projectResourceViews : projectDayGridViews}
      resources={viewMode === 'resources' ? visibleResources : undefined}
      selectable={!print && canCreate}
      selectAllow={(selection) => viewMode !== 'resources' || Boolean(selection.resource && (canCreateResource?.(selection.resource.id) ?? true))}
      select={(selection) => {
        if (viewMode === 'resources' && (!selection.resource || !(canCreateResource?.(selection.resource.id) ?? true))) return
        onCreate?.(leaveDatesFromSelection(selection.startStr, selection.endStr, selection.allDay), selection.resource?.id)
      }}
      datesSet={() => { if (print) requestAnimationFrame(() => requestAnimationFrame(() => onReady?.())) }}
      schedulerLicenseKey="AGPL-My-Frontend-And-Backend-Are-Open-Source"
      slotMinWidth={print && definition.kind === 'timeline' ? scope === 'year' ? 56 : scope === 'twoMonths' ? 14 : viewMode === 'resources' ? 12 : 24 : undefined}
    />
  </div>
}
