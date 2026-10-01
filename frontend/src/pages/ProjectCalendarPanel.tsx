import FullCalendar from '@fullcalendar/react'
import interactionPlugin from '@fullcalendar/react/interaction'
import classicThemePlugin from '@fullcalendar/react/themes/classic'
import resourceTimelinePlugin from '@fullcalendar/react-scheduler/resource-timeline'
import enGbLocale from '@fullcalendar/react/locales/en-gb'
import frLocale from '@fullcalendar/react/locales/fr'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCallback, useMemo, useRef, useState } from 'react'
import type { CalendarEvent, CalendarFilter } from '../api/employees'
import { createProjectCalendarLeave, deleteProjectCalendarLeave, getProjectCalendar, getProjectCalendarFilters, getProjectCalendarParticipants, updateProjectCalendarLeave } from '../api/projectCalendar'
import { createTeamCalendarLeave, deleteTeamCalendarLeave, getTeamCalendar, getTeamCalendarFilters, getTeamCalendarParticipants, updateTeamCalendarLeave } from '../api/teamCalendar'
import { toFullCalendarEvent } from '../calendar/fullCalendarAdapter'
import { movedLeave, resizedLeave } from '../calendar/leaveCalendarMutation'
import { CalendarPluginFilters, effectiveCalendarFilterValues, type CalendarFilterValues } from '../calendar/CalendarPluginFilters'
import { leaveDatesFromSelection } from '../calendar/leaveSelection'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { EmployeeCalendar } from './EmployeeCalendar'
import { EmployeeLeaveSheet } from './EmployeeLeaveSheet'
import { LeaveTable } from './EmployeeLeaves'
import { leaveFromEvent, rangeLabel } from './leaveCalendarPresentation'
import { projectCalendarRange, projectCalendarScopeOrder, projectCalendarScopes, projectResourceViews, shiftProjectCalendarAnchor, type ProjectCalendarScope } from './projectCalendarScopes'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeLeaves.module.css'

type Mode = 'calendar' | 'list' | 'resources'
type Dates = { start_date: string; end_date: string }
const emptyFilters: CalendarFilter[] = []

export function ProjectCalendarPanel({ projectId, teamId }: { projectId?: string; teamId?: string }) {
  const id = teamId ?? projectId ?? ''
  const { language, t } = useTranslation()
  const [mode, setMode] = useState<Mode>('calendar')
  const [scope, setScope] = useState<ProjectCalendarScope>('month')
  const [anchor, setAnchor] = useState(() => new Date())
  const [filterValues, setFilterValues] = useState<CalendarFilterValues>({})
  const [selected, setSelected] = useState<CalendarEvent | null>(null)
  const [creating, setCreating] = useState<Dates | null>(null)
  const [employeeId, setEmployeeId] = useState('')
  const suppressClick = useRef(false)
  const range = useMemo(() => projectCalendarRange(scope, anchor), [scope, anchor])
  const participantsLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendarParticipants(value, signal) : getProjectCalendarParticipants(value, signal), [teamId])
  const filtersLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendarFilters(value, signal) : getProjectCalendarFilters(value, signal), [teamId])
  const participants = useEmployeeResource(id, participantsLoader)
  const filters = useEmployeeResource(id, filtersLoader)
  const effectiveFilters = useMemo(() => effectiveCalendarFilterValues(filters.data ?? emptyFilters, filterValues), [filters.data, filterValues])
  const calendarLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendar(value, range, effectiveFilters, signal) : getProjectCalendar(value, range, effectiveFilters, signal), [teamId, range, effectiveFilters])
  const events = useEmployeeResource(id, calendarLoader)
  const editableParticipants = participants.data?.filter((item) => item.capabilities.can_add) ?? []
  const currentEmployeeId = selected ? String(selected.metadata.employee_id) : employeeId
  const currentParticipant = participants.data?.find((item) => String(item.id) === currentEmployeeId)
  const canCreate = editableParticipants.length > 0
  const canChangeEvent = useCallback((event: CalendarEvent) => Boolean(teamId && event.source === 'core' && event.kind === 'leave' && participants.data?.some((item) => item.id === Number(event.metadata.employee_id) && item.capabilities.can_change)), [teamId, participants.data])
  const canChange = Boolean(teamId && participants.data?.some((item) => item.capabilities.can_change))
  const changeDates = async (event: CalendarEvent, value: import('../api/employees').LeaveWrite) => {
    if (!canChangeEvent(event)) throw new Error('Leave cannot be changed')
    await updateTeamCalendarLeave(id, Number(event.metadata.leave_id), value)
    void events.refresh()
  }
  const openCreate = (dates: Dates = { start_date: '', end_date: '' }, resourceId?: string) => {
    if (!canCreate || (resourceId && !editableParticipants.some((item) => String(item.id) === resourceId))) return
    setSelected(null)
    setEmployeeId(resourceId ?? String(editableParticipants[0].id))
    setCreating(dates)
  }
  const openEvent = (event: CalendarEvent) => { if (!suppressClick.current && event.source === 'core' && event.kind === 'leave') { setCreating(null); setSelected(event) } }
  const stopGesture = () => { window.setTimeout(() => { suppressClick.current = false }, 250) }
  const close = () => { setSelected(null); setCreating(null) }
  const listEvents = (events.data ?? []).filter((event) => event.source === 'core' && event.kind === 'leave')
  const listLeaves = listEvents.map(leaveFromEvent)
  const employeeNames = new Map(listEvents.map((event) => [Number(event.metadata.leave_id), participants.data?.find((item) => item.id === Number(event.metadata.employee_id))?.title ?? '—']))
  const projectEmployeeNames = new Map((participants.data ?? []).map((item) => [item.id, item.title]))
  const resourceEvents = (events.data ?? []).map((event) => {
    const mapped = toFullCalendarEvent(event)
    return event.kind === 'leave' ? toFullCalendarEvent(event, canChangeEvent(event)) : { ...mapped, resourceIds: (participants.data ?? []).map((item) => String(item.id)) }
  })

  return <section className={styles.root}>
    <div className={styles.toolbar}>
      <div aria-label={t('project.calendar')} className={styles.segmented} role="group">
        {(['calendar', 'list', 'resources'] as const).map((item) => <Button aria-pressed={mode === item} key={item} onClick={() => setMode(item)} size="sm" variant={mode === item ? 'default' : 'ghost'}>{t(`projectCalendar.${item}`)}</Button>)}
      </div>
      {canCreate && <Button onClick={() => openCreate()} size="sm"><Plus aria-hidden="true" />{t('leaves.add')}</Button>}
    </div>
    <div className={styles.calendarToolbar}>
      <div className={styles.navigation}>
        <Button aria-label={t('leaves.previous')} onClick={() => setAnchor((date) => shiftProjectCalendarAnchor(date, scope, -1))} size="icon-sm" variant="ghost"><ChevronLeft aria-hidden="true" /></Button>
        <Button onClick={() => setAnchor(new Date())} size="sm" variant="ghost">{t('leaves.today')}</Button>
        <Button aria-label={t('leaves.next')} onClick={() => setAnchor((date) => shiftProjectCalendarAnchor(date, scope, 1))} size="icon-sm" variant="ghost"><ChevronRight aria-hidden="true" /></Button>
        <strong>{rangeLabel(range, language)}</strong>
      </div>
      {mode !== 'list' && <div aria-label={t('projectCalendar.period')} className={styles.segmented} role="group">{projectCalendarScopeOrder.map((item) => <Button aria-pressed={scope === item} key={item} onClick={() => setScope(item)} size="sm" variant={scope === item ? 'secondary' : 'ghost'}>{t(projectCalendarScopes[item].label)}</Button>)}</div>}
    </div>
    {Boolean(filters.error) && <div className={styles.error} role="alert">{t('leaves.pluginFiltersError')} <Button onClick={filters.retry} size="sm">{t('common.retry')}</Button></div>}
    <CalendarPluginFilters definitions={filters.data ?? []} onChange={setFilterValues} values={filterValues} />
    {Boolean(participants.error) && <div className={styles.error} role="alert">{t('projectCalendar.participantsError')} <Button onClick={participants.retry} size="sm">{t('common.retry')}</Button></div>}
    {events.loading && <p role="status">{t('leaves.loading')}</p>}
    {Boolean(events.error) && <div className={styles.error} role="alert">{t('leaves.error')} <Button onClick={events.retry} size="sm">{t('common.retry')}</Button></div>}
    {Boolean(events.refreshError) && <div className={styles.error} role="alert">{t('leaves.refreshError')} <Button onClick={() => void events.refresh()} size="sm">{t('common.retry')}</Button></div>}
    {events.data && mode === 'calendar' && <EmployeeCalendar anchor={anchor} events={events.data} onOpen={openEvent} onCreate={(dates) => openCreate(dates)} onChangeDates={changeDates} canCreate={canCreate} canChange={canChange} canChangeEvent={canChangeEvent} projectScope={scope} projectEmployeeNames={projectEmployeeNames} />}
    {events.data && mode === 'list' && <LeaveTable leaves={listLeaves} employeeNames={employeeNames} onOpen={(leave) => { const event = listEvents.find((item) => Number(item.metadata.leave_id) === leave.id); if (event) openEvent(event) }} />}
    {events.data && mode === 'resources' && participants.data && <div aria-label={t('projectCalendar.resources')} className={styles.fullCalendar} role="region">
      <FullCalendar
        editable={canChange}
        eventDragStart={() => { suppressClick.current = true }}
        eventDragStop={stopGesture}
        eventResizeStart={() => { suppressClick.current = true }}
        eventResizeStop={stopGesture}
        eventResizableFromStart
        eventDrop={(info) => {
          const event = events.data?.find((item) => item.id === info.event.id)
          if (!event || !info.oldEvent.startStr || !info.event.startStr) { info.revert(); return }
          void changeDates(event, movedLeave(event, info.oldEvent.startStr, info.event.startStr)).catch(info.revert)
        }}
        eventResize={(info) => {
          const event = events.data?.find((item) => item.id === info.event.id)
          if (!event || !info.oldEvent.startStr || !info.event.startStr || !info.oldEvent.endStr || !info.event.endStr) { info.revert(); return }
          void changeDates(event, resizedLeave(event, info.oldEvent.startStr, info.event.startStr, info.oldEvent.endStr, info.event.endStr)).catch(info.revert)
        }}
        events={resourceEvents}
        eventClick={(info) => { const event = events.data?.find((item) => item.id === info.event.id); if (event) openEvent(event) }}
        eventContent={(info) => {
          const event = events.data?.find((item) => item.id === info.event.id)
          return event?.source === 'core' && event.kind === 'leave'
            ? <button aria-label={t('leaves.open', { name: event.title })} className={styles.fullCalendarEventButton} onClick={(click) => { click.stopPropagation(); openEvent(event) }} type="button">{event.title}</button>
            : <span className={styles.fullCalendarEvent}>{info.event.title}</span>
        }}
        headerToolbar={false}
        initialDate={anchor}
        initialView={projectCalendarScopes[scope].resourceView}
        key={`${scope}:${anchor.getFullYear()}:${anchor.getMonth()}:${anchor.getDate()}`}
        locale={language.startsWith('fr') ? frLocale : enGbLocale}
        plugins={[resourceTimelinePlugin, interactionPlugin, classicThemePlugin]}
        resources={participants.data.map((item) => ({ id: String(item.id), title: item.title }))}
        schedulerLicenseKey="AGPL-My-Frontend-And-Backend-Are-Open-Source"
        selectable={canCreate}
        selectAllow={(selection) => Boolean(selection.resource && editableParticipants.some((item) => String(item.id) === selection.resource?.id))}
        views={projectResourceViews}
        select={(selection) => { if (selection.resource) openCreate(leaveDatesFromSelection(selection.startStr, selection.endStr, selection.allDay), selection.resource.id) }}
      />
    </div>}
    {(selected || creating) && currentEmployeeId && <EmployeeLeaveSheet key={selected?.id ?? 'create'} employeeId={currentEmployeeId} leave={selected ? leaveFromEvent(selected) : null} initialDates={creating ?? undefined} capabilities={currentParticipant?.capabilities ?? { can_add: false, can_change: false, can_delete: false }} employeeOptions={creating ? editableParticipants : undefined} onEmployeeChange={setEmployeeId} createLeave={(employee, value) => teamId ? createTeamCalendarLeave(id, employee, value) : createProjectCalendarLeave(id, employee, value)} updateLeave={(_employee, leaveId, value) => teamId ? updateTeamCalendarLeave(id, leaveId, value) : updateProjectCalendarLeave(id, leaveId, value)} deleteLeave={(_employee, leaveId) => teamId ? deleteTeamCalendarLeave(id, leaveId) : deleteProjectCalendarLeave(id, leaveId)} onClose={close} onSaved={() => { close(); void events.refresh() }} onDeleted={() => { close(); void events.refresh() }} />}
  </section>
}
