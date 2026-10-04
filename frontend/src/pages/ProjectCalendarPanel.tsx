import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import type { CalendarEvent, CalendarFilter } from '../api/employees'
import { createProjectCalendarLeave, deleteProjectCalendarLeave, getProjectCalendar, getProjectCalendarFilters, getProjectCalendarParticipants, updateProjectCalendarLeave } from '../api/projectCalendar'
import { createTeamCalendarLeave, deleteTeamCalendarLeave, getTeamCalendar, getTeamCalendarFilters, getTeamCalendarParticipants, updateTeamCalendarLeave } from '../api/teamCalendar'
import { SharedCalendar, type ResourceVisibilityMode } from '../calendar/SharedCalendar'
import { localToday } from '../calendar/resourceVisibility'
import { CalendarPluginFilters, effectiveCalendarFilterValues, type CalendarFilterValues } from '../calendar/CalendarPluginFilters'
import { useTranslation } from '../i18n/i18n'
import { PrintButton } from '../print/PrintButton'
import type { CalendarPrintState } from '../print/CalendarPrintView'
import { Button } from '../ui/Button'
import { EmployeeCalendar } from './EmployeeCalendar'
import { EmployeeLeaveSheet } from './EmployeeLeaveSheet'
import { LeaveTable } from './EmployeeLeaves'
import { leaveFromEvent, rangeLabel } from './leaveCalendarPresentation'
import { projectCalendarRange, projectCalendarScopeOrder, projectCalendarScopes, projectCalendarViewDefinition, shiftProjectCalendarAnchor, type ProjectCalendarScope } from './projectCalendarScopes'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeLeaves.module.css'

type Mode = 'calendar' | 'list' | 'resources'
type Dates = { start_date: string; end_date: string }
const emptyFilters: CalendarFilter[] = []

export function ProjectCalendarPanel({ projectId, teamId, contextName }: { projectId?: string; teamId?: string; contextName?: string }) {
  const id = teamId ?? projectId ?? ''
  const { language, t } = useTranslation()
  const [mode, setMode] = useState<Mode>('calendar')
  const [resourceVisibilityMode, setResourceVisibilityMode] = useState<ResourceVisibilityMode>('period')
  const [scope, setScope] = useState<ProjectCalendarScope>('month')
  const [anchor, setAnchor] = useState(() => new Date())
  const [filterValues, setFilterValues] = useState<CalendarFilterValues>({})
  const [selected, setSelected] = useState<CalendarEvent | null>(null)
  const [creating, setCreating] = useState<Dates | null>(null)
  const [employeeId, setEmployeeId] = useState('')
  const range = useMemo(() => projectCalendarRange(scope, anchor), [scope, anchor])
  const participantsLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendarParticipants(value, signal) : getProjectCalendarParticipants(value, signal), [teamId])
  const filtersLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendarFilters(value, signal) : getProjectCalendarFilters(value, signal), [teamId])
  const participants = useEmployeeResource(id, participantsLoader)
  const filters = useEmployeeResource(id, filtersLoader)
  const effectiveFilters = useMemo(() => effectiveCalendarFilterValues(filters.data ?? emptyFilters, filterValues), [filters.data, filterValues])
  const calendarLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendar(value, range, effectiveFilters, signal) : getProjectCalendar(value, range, effectiveFilters, signal), [teamId, range, effectiveFilters])
  const events = useEmployeeResource(id, calendarLoader)
  const today = localToday()
  const todayLoader = useCallback((value: string, signal: AbortSignal) => teamId ? getTeamCalendar(value, { from: today, to: today }, effectiveFilters, signal) : getProjectCalendar(value, { from: today, to: today }, effectiveFilters, signal), [teamId, today, effectiveFilters])
  const todayCalendar = useEmployeeResource(id, todayLoader, mode === 'resources' && resourceVisibilityMode === 'today')
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
    if (resourceVisibilityMode === 'today') void todayCalendar.refresh()
  }
  const openCreate = (dates: Dates = { start_date: '', end_date: '' }, resourceId?: string) => {
    if (!canCreate || (resourceId && !editableParticipants.some((item) => String(item.id) === resourceId))) return
    setSelected(null)
    setEmployeeId(resourceId ?? String(editableParticipants[0].id))
    setCreating(dates)
  }
  const openEvent = (event: CalendarEvent) => { if (event.source === 'core' && event.kind === 'leave') { setCreating(null); setSelected(event) } }
  const close = () => { setSelected(null); setCreating(null) }
  const listEvents = (events.data ?? []).filter((event) => event.source === 'core' && event.kind === 'leave')
  const listLeaves = listEvents.map(leaveFromEvent)
  const employeeNames = new Map(listEvents.map((event) => [Number(event.metadata.leave_id), participants.data?.find((item) => item.id === Number(event.metadata.employee_id))?.title ?? '—']))
  const projectEmployeeNames = new Map((participants.data ?? []).map((item) => [item.id, item.title]))

  return <section className={styles.root}>
    <div className={styles.toolbar}>
      <div aria-label={t('project.calendar')} className={styles.segmented} role="group">
        {(['calendar', 'list', 'resources'] as const).map((item) => <Button aria-pressed={mode === item} key={item} onClick={() => setMode(item)} size="sm" variant={mode === item ? 'default' : 'ghost'}>{t(`projectCalendar.${item}`)}</Button>)}
      </div>
      {events.data && mode !== 'list' && <PrintButton disabled={mode === 'resources' && resourceVisibilityMode === 'today' && !todayCalendar.data} createRequest={() => ({ renderer: 'calendar', title: `${teamId ? t('team.leaves') : t('project.calendar')} — ${contextName ?? id}`, state: { scope, viewType: projectCalendarViewDefinition(scope, mode === 'resources' ? 'resources' : 'calendar').key, mode: mode === 'resources' ? 'resources' : 'calendar', range, events: events.data ?? [], resources: participants.data?.map((item) => ({ id: String(item.id), title: item.title })), todayEvents: todayCalendar.data ?? undefined, resourceVisibilityMode, employeeNames: Object.fromEntries(projectEmployeeNames), filters: effectiveFilters, selectedId: selected?.id ?? null } satisfies CalendarPrintState })} />}
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
    {mode === 'resources' && resourceVisibilityMode === 'today' && Boolean(todayCalendar.error) && <div className={styles.error} role="alert">{t('leaves.error')} <Button onClick={todayCalendar.retry} size="sm">{t('common.retry')}</Button></div>}
    {events.data && mode === 'calendar' && <EmployeeCalendar anchor={anchor} events={events.data} onOpen={openEvent} onCreate={(dates) => openCreate(dates)} onChangeDates={changeDates} canCreate={canCreate} canChange={canChange} canChangeEvent={canChangeEvent} projectScope={scope} projectEmployeeNames={projectEmployeeNames} />}
    {events.data && mode === 'list' && <LeaveTable leaves={listLeaves} employeeNames={employeeNames} onOpen={(leave) => { const event = listEvents.find((item) => Number(item.metadata.leave_id) === leave.id); if (event) openEvent(event) }} />}
    {events.data && mode === 'resources' && participants.data && <SharedCalendar anchor={anchor} scope={scope} viewMode="resources" events={events.data} resources={participants.data.map((item) => ({ id: String(item.id), title: item.title }))} todayEvents={todayCalendar.data ?? undefined} resourceVisibilityMode={resourceVisibilityMode} onResourceVisibilityModeChange={setResourceVisibilityMode} onOpen={openEvent} onCreate={openCreate} onChangeDates={changeDates} canCreate={canCreate} canChange={canChange} canChangeEvent={canChangeEvent} canCreateResource={(resourceId) => editableParticipants.some((item) => String(item.id) === resourceId)} />}
    {(selected || creating) && currentEmployeeId && <EmployeeLeaveSheet key={selected?.id ?? 'create'} employeeId={currentEmployeeId} leave={selected ? leaveFromEvent(selected) : null} initialDates={creating ?? undefined} capabilities={currentParticipant?.capabilities ?? { can_add: false, can_change: false, can_delete: false }} employeeOptions={creating ? editableParticipants : undefined} onEmployeeChange={setEmployeeId} createLeave={(employee, value) => teamId ? createTeamCalendarLeave(id, employee, value) : createProjectCalendarLeave(id, employee, value)} updateLeave={(_employee, leaveId, value) => teamId ? updateTeamCalendarLeave(id, leaveId, value) : updateProjectCalendarLeave(id, leaveId, value)} deleteLeave={(_employee, leaveId) => teamId ? deleteTeamCalendarLeave(id, leaveId) : deleteProjectCalendarLeave(id, leaveId)} onClose={close} onSaved={() => { close(); void events.refresh(); if (resourceVisibilityMode === 'today') void todayCalendar.refresh() }} onDeleted={() => { close(); void events.refresh(); if (resourceVisibilityMode === 'today') void todayCalendar.refresh() }} />}
  </section>
}
