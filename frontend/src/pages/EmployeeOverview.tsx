import { useRef, useState, type ReactNode, type RefObject } from 'react'
import { Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getEmployeeHierarchy,
  deleteEmployeeHierarchyRelation,
  deleteEmployeeStatus,
  getEmployeeStatusOptions,
  getEmployeeStatuses,
  type EmployeeHierarchyDirection,
  type EmployeeHierarchyRelation,
  type EmployeeStatusHistoryItem,
} from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { EmployeeHierarchySheet } from './EmployeeHierarchySheet'
import { EmployeeStatusSheet } from './EmployeeStatusSheet'
import { Alert } from '../ui/Alert'
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
  const statusOptions = useEmployeeResource(employeeId, getEmployeeStatusOptions)
  const hierarchy = useEmployeeResource(employeeId, getEmployeeHierarchy)
  const [editingStatus, setEditingStatus] = useState<EmployeeStatusHistoryItem | null | undefined>(undefined)
  const [deletingStatus, setDeletingStatus] = useState<EmployeeStatusHistoryItem | null>(null)
  const [editing, setEditing] = useState<{ direction: EmployeeHierarchyDirection; relation: EmployeeHierarchyRelation | null } | null>(null)
  const [deleting, setDeleting] = useState<{ direction: EmployeeHierarchyDirection; relation: EmployeeHierarchyRelation } | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const statusFocus = useRef<HTMLElement | null>(null)
  const statusSection = useRef<HTMLElement | null>(null)
  const hierarchySection = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const statusMutation = useMutation()
  const mutationError = mutation.error ? normalizeMutationError(mutation.error) : null
  const canAdd = Boolean(employee.capabilities?.can_change && hierarchy.data?.capabilities?.can_add)
  const canEdit = Boolean(employee.capabilities?.can_change && hierarchy.data?.capabilities?.can_change)
  const canDelete = Boolean(employee.capabilities?.can_change && hierarchy.data?.capabilities?.can_delete)
  const statusCanAdd = Boolean(employee.capabilities?.can_change && statusOptions.data?.capabilities.can_add)
  const statusCanEdit = Boolean(employee.capabilities?.can_change && statusOptions.data?.capabilities.can_change)
  const statusCanDelete = Boolean(employee.capabilities?.can_change && statusOptions.data?.capabilities.can_delete)
  async function removeStatus() {
    if (!deletingStatus) return
    const result = await statusMutation.run(() => deleteEmployeeStatus(employeeId, deletingStatus.id))
    if (result) {
      statusFocus.current = statusSection.current
      setDeletingStatus(null)
      void statuses.refresh()
    }
  }
  async function removeRelation() {
    if (!deleting) return
    const result = await mutation.run(() => deleteEmployeeHierarchyRelation(employeeId, deleting.relation.id))
    if (result) {
      focus.current = hierarchySection.current
      setDeleting(null)
      void hierarchy.refresh()
    }
  }

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
        <section ref={statusSection} tabIndex={-1} className={styles.column} aria-labelledby="employee-status-heading">
          <div className={styles.relationshipHeading}><MiniHeading id="employee-status-heading">{t('employee.statuses')}</MiniHeading>
            {statusCanAdd && <Button size="xs" variant="ghost" onClick={(event) => { statusFocus.current = event.currentTarget; setEditingStatus(null) }}><Plus aria-hidden="true" />{t('employee.addStatus')}</Button>}
          </div>
          <SecondaryResource resource={statuses}>{(items) => <StatusHistory items={items} canEdit={statusCanEdit} canDelete={statusCanDelete} focusRef={statusFocus}
            actionOpen={editingStatus !== undefined || Boolean(deletingStatus)} onEdit={setEditingStatus} onDelete={setDeletingStatus} />}</SecondaryResource>
          {Boolean(statuses.refreshError) && <div className={styles.localError} role="alert">{t('employee.secondaryError')} <Button size="xs" variant="ghost" onClick={() => void statuses.refresh()}>{t('common.retry')}</Button></div>}
          {Boolean(statusOptions.error) && <div className={styles.localError} role="alert">{t('employee.statusOptionsError')} <Button size="xs" variant="ghost" onClick={statusOptions.retry}>{t('common.retry')}</Button></div>}
        </section>
        <section ref={hierarchySection} tabIndex={-1} className={styles.column} aria-labelledby="employee-hierarchy-heading">
          <MiniHeading id="employee-hierarchy-heading">{t('employee.hierarchy')}</MiniHeading>
          <SecondaryResource resource={hierarchy}>{(value) => <>
            <RelationshipHistory items={value.superiors} title={t('employee.superiors')} direction="superior" canAdd={canAdd} canEdit={canEdit} canDelete={canDelete} focus={focus}
              onAdd={() => setEditing({ direction: 'superior', relation: null })} onEdit={(relation) => setEditing({ direction: 'superior', relation })} onDelete={(relation) => setDeleting({ direction: 'superior', relation })} actionOpen={Boolean(editing || deleting)} />
            <RelationshipHistory items={value.subordinates} title={t('employee.subordinates')} direction="subordinate" canAdd={canAdd} canEdit={canEdit} canDelete={canDelete} focus={focus}
              onAdd={() => setEditing({ direction: 'subordinate', relation: null })} onEdit={(relation) => setEditing({ direction: 'subordinate', relation })} onDelete={(relation) => setDeleting({ direction: 'subordinate', relation })} actionOpen={Boolean(editing || deleting)} />
          </>}</SecondaryResource>
          {Boolean(hierarchy.refreshError) && <div className={styles.localError} role="alert">{t('employee.secondaryError')} <Button size="xs" variant="ghost" onClick={() => void hierarchy.refresh()}>{t('common.retry')}</Button></div>}
        </section>
      </div>
      {editingStatus !== undefined && statusOptions.data && <EmployeeStatusSheet employeeId={employeeId} status={editingStatus} options={statusOptions.data}
        defaultDates={{ start_date: employee.entry_date, end_date: employee.exit_date }} returnFocus={statusFocus}
        onClose={() => setEditingStatus(undefined)} onSaved={() => { setEditingStatus(undefined); void statuses.refresh() }} />}
      {deletingStatus && <ConfirmDialog title={t('employee.deleteStatus')}
        description={t('employee.deleteStatusConfirm', { name: deletingStatus.type.name })}
        pending={statusMutation.pending} error={statusMutation.error ? <Alert tone="danger">{[...normalizeMutationError(statusMutation.error).messages, ...Object.values(normalizeMutationError(statusMutation.error).fields).flat()].join(' ') || t('employee.statusSaveError')}</Alert> : undefined}
        onCancel={() => setDeletingStatus(null)} onConfirm={() => void removeStatus()} returnFocus={statusFocus} />}
      {editing && <EmployeeHierarchySheet employeeId={employeeId} direction={editing.direction} relation={editing.relation}
        defaultDates={{ start_date: employee.entry_date, end_date: employee.exit_date }} returnFocus={focus}
        onClose={() => setEditing(null)} onSaved={() => { setEditing(null); void hierarchy.refresh() }} />}
      {deleting && <ConfirmDialog title={t(deleting.direction === 'superior' ? 'employee.removeSuperior' : 'employee.removeSubordinate')}
        description={t('employee.removeHierarchyConfirm', { name: fullName(deleting.relation.employee) })}
        pending={mutation.pending} error={mutationError ? <Alert tone="danger">{[...mutationError.messages, ...Object.values(mutationError.fields).flat()].join(' ') || t('employee.hierarchySaveError')}</Alert> : undefined}
        onCancel={() => setDeleting(null)} onConfirm={() => void removeRelation()} returnFocus={focus} />}
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

function StatusHistory({ items, canEdit, canDelete, focusRef, actionOpen, onEdit, onDelete }: {
  items: EmployeeStatusHistoryItem[]; canEdit: boolean; canDelete: boolean; focusRef: RefObject<HTMLElement | null>
  actionOpen: boolean; onEdit: (item: EmployeeStatusHistoryItem) => void; onDelete: (item: EmployeeStatusHistoryItem) => void
}) {
  const { t } = useTranslation()
  return <HistoryList
    current={items.filter((item) => item.is_active)}
    empty={t('employee.noCurrentStatus')}
    previous={items.filter((item) => !item.is_active)}
    render={(item) => <div className={styles.relationRow} key={item.id}><div className={styles.relation}><strong>{item.type.name || item.type.code}</strong><small>{period(item.start_date, item.end_date, t)}</small></div>
      {(canEdit || canDelete) && <ItemActionMenu label={t('common.actionsFor', { name: item.type.name || item.type.code })} canChange={canEdit} canDelete={canDelete}
        onOpen={() => {}} onTrigger={(trigger) => { focusRef.current = trigger }} finalFocus={() => !actionOpen}
        onEdit={() => onEdit(item)} onDelete={() => onDelete(item)} />}</div>}
  />
}

function RelationshipHistory({ items, title, direction, canAdd, canEdit, canDelete, focus: focusRef, onAdd, onEdit, onDelete, actionOpen }: {
  items: EmployeeHierarchyRelation[]; title: string; direction: EmployeeHierarchyDirection; canAdd: boolean; canEdit: boolean; canDelete: boolean
  focus: RefObject<HTMLElement | null>; onAdd: () => void; onEdit: (relation: EmployeeHierarchyRelation) => void
  onDelete: (relation: EmployeeHierarchyRelation) => void; actionOpen: boolean
}) {
  const { t } = useTranslation()
  return <div className={styles.relationshipGroup}>
    <div className={styles.relationshipHeading}><h4>{title}</h4>{canAdd && <Button size="xs" variant="ghost" onClick={(event) => { focusRef.current = event.currentTarget; onAdd() }}><Plus aria-hidden="true" />{t(direction === 'superior' ? 'employee.addSuperior' : 'employee.addSubordinate')}</Button>}</div>
    <HistoryList
      current={items.filter((item) => item.is_active)}
      empty={t('employee.noneCurrently')}
      previous={items.filter((item) => !item.is_active)}
      render={(item) => <div className={styles.relationRow} key={item.id}><div className={styles.relation}>{item.can_view === false ? <strong>{fullName(item.employee)}</strong> : <Link to={`/employees/${item.employee.id}`}>{fullName(item.employee)}</Link>}<small>{period(item.start_date, item.end_date, t)}</small></div>
        {(canEdit || canDelete) && item.is_active && <ItemActionMenu label={t('common.actionsFor', { name: fullName(item.employee) })} canChange={canEdit} canDelete={canDelete}
          onOpen={() => {}} onTrigger={(trigger) => { focusRef.current = trigger }} finalFocus={() => !actionOpen}
          onEdit={() => onEdit(item)} onDelete={() => onDelete(item)} />}</div>}
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
