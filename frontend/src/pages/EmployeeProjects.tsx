import { useState, type ReactNode } from 'react'
import { getEmployeeMilestones, getEmployeeProjectParticipations, type EmployeeProjectParticipation } from '../api/employees'
import { EmployeeGanttPanel } from '../gantt/EmployeeGanttPanel'
import { PersistentCollapsibleSection } from '../components/common/PersistentCollapsibleSection'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { StatusBadge } from '../ui/StatusBadge'
import { useEmployeeDetail } from './employeeDetailContext'
import styles from './EmployeeDetailPage.module.css'
import { EmployeeMilestones } from './EmployeeMilestones'
import { EmployeeProjectWorkload } from './EmployeeProjectWorkload'
import { useEmployeeResource, type EmployeeResource } from './useEmployeeResource'

export function EmployeeProjects() {
  const { employeeId } = useEmployeeDetail()
  const { t } = useTranslation()
  const milestones = useEmployeeResource(employeeId, getEmployeeMilestones)
  const projects = useEmployeeResource(employeeId, getEmployeeProjectParticipations)
  const [mode, setMode] = useState<'list' | 'gantt'>('list')

  return <>
    <div className={styles.projectHeading}><h2 className={styles.panelTitle}>{t('employee.navProjects')}</h2>
      <div aria-label={t('gantt.view')} role="group"><Button aria-pressed={mode === 'list'} onClick={() => setMode('list')} size="sm" variant={mode === 'list' ? 'secondary' : 'ghost'}>{t('gantt.list')}</Button><Button aria-pressed={mode === 'gantt'} onClick={() => setMode('gantt')} size="sm" variant={mode === 'gantt' ? 'secondary' : 'ghost'}>{t('gantt.title')}</Button></div>
    </div>
    {mode === 'list' && <>
    <PersistentCollapsibleSection storageKey="labsmanager:employee:milestones-open" title={t('employee.milestones')}>
      <EmployeeMilestones resource={milestones} />
    </PersistentCollapsibleSection>
    <PersistentCollapsibleSection storageKey="labsmanager:employee:project-participations-open" title={t('employee.projects')}>
      <EmployeeProjectWorkload employeeId={employeeId} />
      <SecondaryResource resource={projects}>{(items) => items.length ? <div className={styles.tableScroll} tabIndex={0} role="region" aria-label={t('employee.projects')}>
        <table><thead><tr><th scope="col">{t('employee.project')}</th><th scope="col">{t('employee.role')}</th><th scope="col">{t('employee.period')}</th><th scope="col">{t('employee.quotity')}</th><th scope="col">{t('employee.state')}</th></tr></thead>
          <tbody>{items.map((item) => <ProjectRow item={item} key={item.id} />)}</tbody></table>
      </div> : <p className={styles.muted}>{t('employee.noProjects')}</p>}</SecondaryResource>
    </PersistentCollapsibleSection>
    </>}
    <EmployeeGanttPanel active={mode === 'gantt'} employeeId={employeeId} key={employeeId} participations={projects.data} work={milestones.data} projectError={Boolean(projects.error)} workError={Boolean(milestones.error)} onRetryProjects={projects.retry} onRetryWork={milestones.retry} />
  </>
}

function ProjectRow({ item }: { item: EmployeeProjectParticipation }) {
  const { t } = useTranslation()
  return <tr><th scope="row">{item.project.name}</th><td>{item.role.label}</td><td>{period(item.start_date, item.end_date, t)}</td><td>{quotity(item.quotity)}</td><td><StatusBadge tone={item.is_active ? 'success' : 'neutral'}>{t(item.is_active ? 'employee.current' : 'employee.historical')}</StatusBadge></td></tr>
}

function SecondaryResource<T>({ children, resource }: { children: (data: T) => ReactNode; resource: EmployeeResource<T> }) {
  const { t } = useTranslation()
  if (resource.loading) return <p className={styles.muted} role="status">…</p>
  if (resource.error) return <div className={styles.localError} role="alert"><span>{t('employee.secondaryError')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>
  return resource.data === null ? null : children(resource.data)
}

type Translator = ReturnType<typeof useTranslation>['t']
function period(start: string | null, end: string | null, t: Translator) {
  const date = (value: string) => new Intl.DateTimeFormat(document.documentElement.lang || 'fr', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  if (start && end) return t('employee.fromTo', { start: date(start), end: date(end) })
  if (start) return t('employee.since', { date: date(start) })
  if (end) return t('employee.until', { date: date(end) })
  return '—'
}

function quotity(value: string | null) { return value === null ? '—' : `${new Intl.NumberFormat(document.documentElement.lang || 'fr', { maximumFractionDigits: 1 }).format(Number(value) * 100)} %` }
