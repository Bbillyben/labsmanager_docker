import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import type { EmployeeMilestone, EmployeeMilestoneState } from '../api/employees'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { MilestoneDetailSheet, Progress } from './MilestoneDetailSheet'
import { milestoneStateKey } from './milestonePresentation'
import styles from './EmployeeMilestones.module.css'

type MilestoneResource = {
  data: EmployeeMilestone[] | null
  error: unknown
  loading: boolean
  retry: () => void
}

const groupOrder: EmployeeMilestoneState[] = ['overdue', 'due_soon', 'in_progress', 'planned', 'completed']

export function EmployeeMilestones({ resource }: { resource: MilestoneResource }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<EmployeeMilestone | null>(null)
  const [openGroups, setOpenGroups] = useState<Record<EmployeeMilestoneState, boolean>>({
    overdue: true,
    due_soon: true,
    in_progress: true,
    planned: true,
    completed: false,
  })

  return <div className={styles.tracker}>
    {resource.loading && <p className={styles.muted} role="status">…</p>}
    {Boolean(resource.error) && <div className={styles.error} role="alert"><span>{t('employee.secondaryError')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {resource.data && resource.data.length === 0 && <p className={styles.muted}>{t('employee.milestonesEmpty')}</p>}
    {resource.data && resource.data.length > 0 && <>
      <div className={styles.summary} aria-label={t('employee.milestones')}>
        {groupOrder.map((state) => <span key={state}>{t(milestoneStateKey(state))} <strong>{resource.data!.filter((item) => item.display_state === state).length}</strong></span>)}
      </div>
      <div className={styles.groups}>{groupOrder.map((state) => {
        const items = sortMilestones(state, resource.data!.filter((item) => item.display_state === state))
        if (items.length === 0) return null
        const open = openGroups[state]
        const title = t(milestoneStateKey(state))
        return <section className={styles.group} data-state={state} key={state}>
          <h3><button aria-label={`${title} · ${items.length}`} aria-expanded={open} onClick={() => setOpenGroups((current) => ({ ...current, [state]: !open }))} type="button">
            <span>{title}<span aria-hidden="true"> · </span><strong>{items.length}</strong></span>
            {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
          </button></h3>
          {open && <div className={styles.rows}>{items.map((milestone) => <MilestoneRow key={milestone.id} milestone={milestone} onOpen={() => setSelected(milestone)} />)}</div>}
        </section>
      })}</div>
    </>}
    <MilestoneDetailSheet milestone={selected} onClose={() => setSelected(null)} onDependenciesChanged={resource.retry} />
  </div>
}

function MilestoneRow({ milestone, onOpen }: { milestone: EmployeeMilestone; onOpen: () => void }) {
  const { language, t } = useTranslation()
  return <button aria-label={t('employee.openMilestone', { name: milestone.name })} className={styles.row} onClick={onOpen} type="button">
    <span className={styles.main}>
      <strong>{milestone.name}</strong>
      <small>{milestone.project.name} · {t(milestone.work_kind === 'milestone' ? 'employee.milestone' : 'employee.task')}{milestone.end_date && <> · {formatDate(milestone.end_date, language)}</>}</small>
      {milestone.type === 'q' && <span className={styles.rowProgress}><Progress label={`${t('employee.progress')} — ${milestone.name}`} value={milestone.quotity} /></span>}
    </span>
    <span className={styles.due}>{dueText(milestone, language, t)}</span>
  </button>
}

type Translator = ReturnType<typeof useTranslation>['t']
function dueText(milestone: EmployeeMilestone, language: string, t: Translator) {
  if (milestone.end_date === null || milestone.days_to_due === null) return t('employee.noDeadline')
  if (milestone.display_state === 'completed') return formatDate(milestone.end_date, language)
  if (milestone.days_to_due === 0) return t('employee.dueToday')
  if (milestone.days_to_due < 0) return t('employee.overdueBy', { count: Math.abs(milestone.days_to_due) })
  return t('employee.dueIn', { count: milestone.days_to_due })
}

function formatDate(value: string, language: string) {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}

function sortMilestones(state: EmployeeMilestoneState, items: EmployeeMilestone[]) {
  return [...items].sort((left, right) => {
    if (state === 'overdue') return compareNumber(right.days_to_due, left.days_to_due) || left.id - right.id
    if (state === 'due_soon' || state === 'in_progress') return compareNumber(left.days_to_due, right.days_to_due) || left.id - right.id
    if (state === 'planned') return compareText(left.start_date, right.start_date) || left.id - right.id
    return compareDateDescending(left.end_date, right.end_date) || left.name.localeCompare(right.name) || left.id - right.id
  })
}

function compareNumber(left: number | null, right: number | null) {
  return (left ?? Number.POSITIVE_INFINITY) - (right ?? Number.POSITIVE_INFINITY)
}

function compareText(left: string | null, right: string | null) {
  if (left === right) return 0
  if (left === null) return 1
  if (right === null) return -1
  return left.localeCompare(right)
}

function compareDateDescending(left: string | null, right: string | null) {
  if (left === right) return 0
  if (left === null) return 1
  if (right === null) return -1
  return right.localeCompare(left)
}
