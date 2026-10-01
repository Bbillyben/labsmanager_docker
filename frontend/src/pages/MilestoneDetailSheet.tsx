import { Pencil, X } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { EmployeeMilestoneWrite, PlanningMilestone } from '../api/planning'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { CheckboxRow } from '../components/CheckboxRow'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { useTranslation } from '../i18n/i18n'
import { milestoneStateKey } from './milestonePresentation'
import { MilestoneDependencies } from './MilestoneDependencies'
import type { PlanningMilestoneActions } from './PlanningMilestoneTable'
import styles from './MilestoneDetailSheet.module.css'

export type EmployeeMilestoneEdit = { canChange: boolean; onSave: (value: EmployeeMilestoneWrite) => Promise<PlanningMilestone> }

export function MilestoneDetailSheet({ milestone, onClose, onDependenciesChanged, actions, manageDependencies = false, employeeEdit }: { milestone: PlanningMilestone | null; onClose: () => void; onDependenciesChanged?: () => void; actions?: PlanningMilestoneActions; manageDependencies?: boolean; employeeEdit?: EmployeeMilestoneEdit }) {
  const { language, t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [desc, setDesc] = useState(milestone?.desc ?? '')
  const [percent, setPercent] = useState(milestone ? String(Number(milestone.quotity) * 100) : '0')
  const [status, setStatus] = useState(milestone?.status ?? false)
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null

  function beginEdit() {
    if (!milestone) return
    setDesc(milestone.desc ?? '')
    setPercent(String(Number(milestone.quotity) * 100))
    setStatus(milestone.status)
    setEditing(true)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!milestone || !employeeEdit?.canChange) return
    const result = await mutation.run(() => employeeEdit.onSave({
      desc: desc || null, status,
      ...(milestone.type === 'q' ? { quotity: (Number(percent) / 100).toFixed(3) } : {}),
    }))
    if (result) setEditing(false)
  }

  return <Sheet onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }} open={milestone !== null}>
    {milestone && <SheetContent>
      {(actions?.canChange || actions?.canDelete || milestone.admin_url) && <ItemActionMenu
        label={t('common.actionsFor', { name: milestone.name })}
        canChange={actions?.canChange ?? false} canDelete={actions?.canDelete ?? false} adminUrl={milestone.admin_url}
        onOpen={() => actions?.onMenuOpen?.()}
        onTrigger={actions?.onTrigger} finalFocus={actions?.finalFocus}
        onEdit={() => actions?.onEdit(milestone)} onDelete={() => actions?.onDelete(milestone)} />}
      <SheetClose aria-label={t('common.close')} className={styles.close} disabled={mutation.pending}><X aria-hidden="true" /></SheetClose>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3 pr-8">
        <SheetHeader className="mb-0 min-w-0 flex-1 pr-0">
          <SheetTitle>{milestone.name}</SheetTitle>
          <SheetDescription>
            {t(milestoneStateKey(milestone.display_state))} · {t(milestone.work_kind === 'milestone' ? 'employee.milestone' : 'employee.task')}
          </SheetDescription>
        </SheetHeader>
        {employeeEdit?.canChange && !editing && <Button type="button" size="sm" variant="secondary" onClick={beginEdit}><Pencil aria-hidden="true" />{t('common.edit')}</Button>}
      </div>
      <dl className={styles.details}>
        <Detail label={t('employee.project')}>{milestone.project.can_view ? <Link to={`/projects/${milestone.project.id}`} onClick={onClose}>{milestone.project.name}</Link> : milestone.project.name}</Detail>
        <Detail label={t('employee.state')}>{t(milestoneStateKey(milestone.display_state))}</Detail>
        <Detail label={t('employee.workType')}>{t(milestone.work_kind === 'milestone' ? 'employee.milestone' : 'employee.task')}</Detail>
        <Detail label={t('employee.milestoneType')}>{t(milestone.type === 'q' ? 'employee.quantifiable' : 'employee.notQuantifiable')}</Detail>
        {milestone.start_date && <Detail label={t('employee.startDate')}>{formatDate(milestone.start_date, language)}</Detail>}
        <Detail label={t('employee.deadline')}>{milestone.end_date ? formatDate(milestone.end_date, language) : t('employee.noDeadline')}</Detail>
        {milestone.type === 'q' && <Detail label={t('employee.progress')}><Progress value={milestone.quotity} label={t('employee.progress')} /></Detail>}
      </dl>

      {milestone.desc && !editing && <section className={styles.block}>
        <h3>{t('employee.description')}</h3>
        <p className={styles.description}>{milestone.desc}</p>
      </section>}

      {editing && employeeEdit?.canChange && <form className="grid gap-4" onSubmit={(event) => void submit(event)} aria-busy={mutation.pending}>
        <p className="text-sm text-muted-foreground">{t('planning.employeeEditDescription')}</p>
        {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t(`genericInfo.error.${error.kind}`)}</Alert>}
        <label className="grid gap-1">{t('employee.description')}<Textarea value={desc} disabled={mutation.pending} onChange={(event) => setDesc(event.target.value)} /></label>
        {milestone.type === 'q' && <label className="grid gap-1">{t('employee.progress')} (%)<Input type="number" min="0" max="100" step="0.1" required value={percent} disabled={mutation.pending} onChange={(event) => setPercent(event.target.value)} /></label>}
        <CheckboxRow checked={status} disabled={mutation.pending} onChange={(event) => setStatus(event.target.checked)}>{t('planning.completed')}</CheckboxRow>
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={mutation.pending} onClick={() => setEditing(false)}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending}>{t('common.save')}</Button></div>
      </form>}

      <section className={styles.block}>
        <h3>{t('employee.assignees')}</h3>
        <ul className={styles.people}>{milestone.employees.map((employee) => {
          const name = `${employee.first_name} ${employee.last_name}`
          return <li key={employee.id}>{employee.can_view ? <Link to={`/employees/${employee.id}`}>{name}</Link> : name}</li>
        })}</ul>
      </section>
      <MilestoneDependencies key={milestone.id} milestone={milestone} onChanged={onDependenciesChanged} allowChanges={manageDependencies} />
    </SheetContent>}
  </Sheet>
}

function Detail({ children, label }: { children: ReactNode; label: string }) {
  return <div><dt>{label}</dt><dd>{children}</dd></div>
}

export function Progress({ label, value }: { label: string; value: string }) {
  const percent = Math.max(0, Math.min(100, Number(value) * 100))
  return <span className={styles.progress}>
    <progress aria-label={label} max="100" value={percent} />
    <span>{new Intl.NumberFormat(document.documentElement.lang || 'fr', { maximumFractionDigits: 1 }).format(percent)} %</span>
  </span>
}

function formatDate(value: string, language: string) {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}
