import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  getEmployeeHierarchy,
  getEmployeeStatuses,
  type EmployeeHierarchyRelation,
  type EmployeeStatusHistoryItem,
} from '../api/employees'
import { EmployeeGenericInfo } from './EmployeeGenericInfo'
import { CopyableValue } from '../components/common/CopyableValue'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { useEmployeeDetail } from './employeeDetailContext'
import styles from './EmployeeDetailPage.module.css'
import { useEmployeeResource, type EmployeeResource } from './useEmployeeResource'

export function EmployeeOverview() {
  const { employee, employeeId } = useEmployeeDetail()
  const { t } = useTranslation()
  const statuses = useEmployeeResource(employeeId, getEmployeeStatuses)
  const hierarchy = useEmployeeResource(employeeId, getEmployeeHierarchy)

  return <section aria-labelledby="employee-general-heading" className={styles.overviewSection}>
    <h2 className={styles.overviewHeading} id="employee-general-heading">{t('employee.general')}</h2>
      <div className={styles.summaryGrid}>
        <section className={styles.column} aria-labelledby="employee-information-heading">
          <MiniHeading id="employee-information-heading">{t('employee.information')}</MiniHeading>
          <dl className={styles.details}>
            <InfoRow label={t('employee.identity')}><CopyableValue value={fullName(employee)} /></InfoRow>
            <DateInfo label={t('employee.birthDate')} value={employee.birth_date} />
            <InfoRow label={t('employee.email')}><CopyableValue value={employee.email}>{employee.email ? <a href={`mailto:${employee.email}`}>{employee.email}</a> : '—'}</CopyableValue></InfoRow>
            <DateInfo label={t('employee.entryDate')} value={employee.entry_date} />
            <DateInfo label={t('employee.exitDate')} value={employee.exit_date} />
            <InfoRow label={t('employee.activity')}>{t(employee.is_active ? 'employee.active' : 'employee.inactive')}</InfoRow>
          </dl>
          <EmployeeGenericInfo employeeId={employeeId} key={employeeId} />
          <div className={styles.indicators}>
            <Indicator label={t('employee.contractQuotity')} value={quotity(employee.contract_quotity)} />
            <Indicator label={t('employee.projectQuotity')} value={quotity(employee.project_quotity)} />
            <Indicator label={t('employee.contributionQuotity')} value={quotity(employee.contribution_quotity)} />
            <Indicator label={t('employee.activeMilestones')} value={String(employee.active_milestones_count)} />
          </div>
        </section>
        <section className={styles.column} aria-labelledby="employee-status-heading">
          <MiniHeading id="employee-status-heading">{t('employee.statuses')}</MiniHeading>
          <SecondaryResource resource={statuses}>{(items) => <StatusHistory items={items} />}</SecondaryResource>
        </section>
        <section className={styles.column} aria-labelledby="employee-hierarchy-heading">
          <MiniHeading id="employee-hierarchy-heading">{t('employee.hierarchy')}</MiniHeading>
          <SecondaryResource resource={hierarchy}>{(value) => <>
            <RelationshipHistory items={value.superiors} title={t('employee.superiors')} />
            <RelationshipHistory items={value.subordinates} title={t('employee.subordinates')} />
          </>}</SecondaryResource>
        </section>
      </div>
  </section>
}

function fullName(employee: { first_name: string; last_name: string }) { return `${employee.first_name} ${employee.last_name}` }
function MiniHeading({ children, id }: { children: ReactNode; id?: string }) { return <h3 className={styles.miniHeading} id={id}>{children}</h3> }
function InfoRow({ children, label }: { children: ReactNode; label: string }) { return <div className={styles.infoRow}><dt>{label}</dt><dd>{children}</dd></div> }

function DateInfo({ label, value }: { label: string; value: string | null }) {
  const formatted = useDate(value)
  return <InfoRow label={label}><CopyableValue value={value ? formatted : null}>{formatted}</CopyableValue></InfoRow>
}

function Indicator({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div> }

function StatusHistory({ items }: { items: EmployeeStatusHistoryItem[] }) {
  const { t } = useTranslation()
  return <HistoryList
    current={items.filter((item) => item.is_active)}
    empty={t('employee.noCurrentStatus')}
    previous={items.filter((item) => !item.is_active)}
    render={(item) => <div className={styles.relation} key={item.id}><strong>{item.type.name || item.type.code}</strong><small>{period(item.start_date, item.end_date, t)}</small></div>}
  />
}

function RelationshipHistory({ items, title }: { items: EmployeeHierarchyRelation[]; title: string }) {
  const { t } = useTranslation()
  return <div className={styles.relationshipGroup}>
    <h4>{title}</h4>
    <HistoryList
      current={items.filter((item) => item.is_active)}
      empty={t('employee.noneCurrently')}
      previous={items.filter((item) => !item.is_active)}
      render={(item) => <div className={styles.relation} key={item.id}><Link to={`/employees/${item.employee.id}`}>{fullName(item.employee)}</Link><small>{period(item.start_date, item.end_date, t)}</small></div>}
    />
  </div>
}

function HistoryList<T extends { id: number }>({ current, empty, previous, render }: { current: T[]; empty: string; previous: T[]; render: (item: T) => ReactNode }) {
  const [expanded, setExpanded] = useState(false)
  const { t } = useTranslation()
  return <>
    <div className={styles.relations}>{current.length ? current.map(render) : <span className={styles.muted}>{empty}</span>}{expanded && previous.map(render)}</div>
    {previous.length > 0 && <Button className={styles.previous} onClick={() => setExpanded((value) => !value)} size="xs" variant="ghost">{expanded ? t('employee.reduceHistory') : t(previous.length === 1 ? 'employee.previousOne' : 'employee.previousMany', { count: previous.length })}</Button>}
  </>
}

function SecondaryResource<T>({ children, resource }: { children: (data: T) => ReactNode; resource: EmployeeResource<T> }) {
  const { t } = useTranslation()
  if (resource.loading) return <p className={styles.muted} role="status">…</p>
  if (resource.error) return <div className={styles.localError} role="alert"><span>{t('employee.secondaryError')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>
  return resource.data === null ? null : children(resource.data)
}

function useDate(value: string | null) {
  const { language } = useTranslation()
  if (!value) return '—'
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}

type Translator = ReturnType<typeof useTranslation>['t']
function period(start: string | null, end: string | null, t: Translator) {
  const date = (value: string) => new Intl.DateTimeFormat(document.documentElement.lang || 'fr', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  if (start && end) return t('employee.fromTo', { start: date(start), end: date(end) })
  if (start) return t('employee.since', { date: date(start) })
  if (end) return t('employee.until', { date: date(end) })
  return '—'
}

function quotity(value: string | null) {
  if (value === null) return '—'
  return `${new Intl.NumberFormat(document.documentElement.lang || 'fr', { maximumFractionDigits: 1 }).format(Number(value) * 100)} %`
}
