import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { getEmployeeCalendar, getEmployeeCalendarFilters, type CalendarEvent, type CalendarFilter, type EmployeeMilestone, type EmployeeProjectParticipation } from '../api/employees'
import { CalendarPluginFilters, effectiveCalendarFilterValues, type CalendarFilterValues } from '../calendar/CalendarPluginFilters'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { MilestoneDetailSheet } from '../pages/MilestoneDetailSheet'
import { adaptEmployeeGantt } from './EmployeeGanttAdapter'
import { LabsManagerGantt } from './LabsManagerGantt'
import type { GanttIdentity } from './model'
import type { GanttWindow } from './SvarGanttAdapter'
import styles from './EmployeeGanttPanel.module.css'

function bounds(anchor: Date, months: 6 | 12 | 24 | 60 | 120): GanttWindow {
  const from = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  const to = new Date(from.getFullYear(), from.getMonth() + months, 0)
  const iso = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  return { from: iso(from), to: iso(to), months }
}

export function EmployeeGanttPanel({ active, employeeId, participations, work, projectError, workError, onRetryProjects, onRetryWork }: {
  active: boolean
  employeeId: string
  participations: EmployeeProjectParticipation[] | null
  work: EmployeeMilestone[] | null
  projectError: boolean
  workError: boolean
  onRetryProjects: () => void
  onRetryWork: () => void
}) {
  const { language, t } = useTranslation()
  const [months, setMonths] = useState<6 | 12 | 24 | 60 | 120>(24)
  const [anchor, setAnchor] = useState(() => new Date())
  const [definitions, setDefinitions] = useState<CalendarFilter[] | null>(null)
  const [filterError, setFilterError] = useState(false)
  const [filterRetry, setFilterRetry] = useState(0)
  const [values, setValues] = useState<CalendarFilterValues>({})
  const [events, setEvents] = useState<CalendarEvent[] | null>(null)
  const [loadedEventKey, setLoadedEventKey] = useState('')
  const [eventError, setEventError] = useState(false)
  const [eventRetry, setEventRetry] = useState(0)
  const [selected, setSelected] = useState<EmployeeMilestone | null>(null)
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const window = useMemo(() => bounds(anchor, months), [anchor, months])
  const filters = useMemo(() => effectiveCalendarFilterValues(definitions ?? [], values), [definitions, values])
  const serializedFilters = JSON.stringify(filters)
  const eventKey = `${employeeId}:${window.from}:${window.to}:${serializedFilters}`
  const data = useMemo(() => adaptEmployeeGantt(participations ?? [], work ?? []), [participations, work])

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.classList.contains('dark')))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    if (!active || definitions !== null) return
    const controller = new AbortController()
    getEmployeeCalendarFilters(employeeId, controller.signal, 'employee-gantt').then((data) => { if (!controller.signal.aborted) { setDefinitions(data); setFilterError(false) } }, () => { if (!controller.signal.aborted) setFilterError(true) })
    return () => controller.abort()
  }, [active, definitions, employeeId, filterRetry])
  useEffect(() => {
    if (!active || definitions === null || (events !== null && loadedEventKey === eventKey)) return
    const controller = new AbortController()
    setEvents(null)
    setEventError(false)
    getEmployeeCalendar(employeeId, window, '', filters, controller.signal, 'employee-gantt').then((data) => { if (!controller.signal.aborted) { setEvents(data); setLoadedEventKey(eventKey) } }, () => { if (!controller.signal.aborted) setEventError(true) })
    return () => controller.abort()
    // serializedFilters is a stable key for the declarative filter values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, definitions, employeeId, window.from, window.to, serializedFilters, eventRetry, events, loadedEventKey, eventKey])
  let navigationStep: number
  if (months === 6) {
    navigationStep = 3
  } else if (months === 12) {
    navigationStep = 6
  } else if (months === 24) {
    navigationStep = 12
  } else if (months === 60) {
    navigationStep = 12
  } else {
    navigationStep = 24
  }
  const move = (direction: number) => setAnchor((current) => new Date(current.getFullYear(), current.getMonth() + direction * navigationStep, 1))
  const select = (identity: GanttIdentity) => {
    if (identity.kind === 'work') setSelected(work?.find((item) => String(item.id) === identity.id) ?? null)
  }
  const rangeLabel = `${new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(new Date(`${window.from}T12:00:00`))} – ${new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(new Date(`${window.to}T12:00:00`))}`

  return <section className={styles.root} hidden={!active}>
    <div className={styles.toolbar}>
      <div className={styles.group}>
        <Button aria-label={t('gantt.previous')} onClick={() => move(-1)} size="icon-sm" variant="ghost"><ChevronLeft aria-hidden="true" /></Button>
        <Button onClick={() => setAnchor(new Date())} size="sm" variant="ghost">{t('gantt.current')}</Button>
        <Button aria-label={t('gantt.next')} onClick={() => move(1)} size="icon-sm" variant="ghost"><ChevronRight aria-hidden="true" /></Button>
        <strong>{rangeLabel}</strong>
      </div>
      <div aria-label={t('gantt.period')} className={styles.group} role="group">
        {([6, 12, 24, 60, 120] as const).map((value) => <Button aria-pressed={months === value} key={value} onClick={() => setMonths(value)} size="sm" variant={months === value ? 'secondary' : 'ghost'}>{t(`gantt.months${value}`)}</Button>)}
      </div>
    </div>
    {filterError && <div role="alert">{t('gantt.filtersError')} <Button onClick={() => setFilterRetry((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    <CalendarPluginFilters definitions={definitions ?? []} onChange={setValues} values={values} />
    {eventError && <div role="alert">{t('gantt.eventsError')} <Button onClick={() => setEventRetry((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {projectError && <div role="alert">{t('employee.secondaryError')} <Button onClick={onRetryProjects} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {workError && <div role="alert">{t('employee.secondaryError')} <Button onClick={onRetryWork} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {(participations === null || work === null || definitions === null || events === null) && !eventError && !projectError && !workError && !filterError && <p role="status">{t('gantt.loading')}</p>}
    {participations !== null && work !== null && events !== null && <LabsManagerGantt data={data} dark={dark} events={events} onSelect={select} window={window} />}
    <MilestoneDetailSheet milestone={selected} onClose={() => setSelected(null)} onDependenciesChanged={onRetryWork} />
  </section>
}
