import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { EmployeeMilestone } from '../api/employees'
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { milestoneStateKey } from './milestonePresentation'
import { MilestoneDependencies } from './MilestoneDependencies'
import styles from './MilestoneDetailSheet.module.css'

export function MilestoneDetailSheet({ milestone, onClose, onDependenciesChanged }: { milestone: EmployeeMilestone | null; onClose: () => void; onDependenciesChanged?: () => void }) {
  const { language, t } = useTranslation()

  return <Sheet onOpenChange={(open) => { if (!open) onClose() }} open={milestone !== null}>
    {milestone && <SheetContent>
      <SheetClose aria-label={t('common.close')} className={styles.close}><X aria-hidden="true" /></SheetClose>
      <SheetHeader>
        <SheetTitle>{milestone.name}</SheetTitle>
        <SheetDescription>
          {t(milestoneStateKey(milestone.display_state))} · {t(milestone.work_kind === 'milestone' ? 'employee.milestone' : 'employee.task')}
        </SheetDescription>
      </SheetHeader>

      <dl className={styles.details}>
        <Detail label={t('employee.project')}>{milestone.project.name}</Detail>
        <Detail label={t('employee.state')}>{t(milestoneStateKey(milestone.display_state))}</Detail>
        <Detail label={t('employee.workType')}>{t(milestone.work_kind === 'milestone' ? 'employee.milestone' : 'employee.task')}</Detail>
        <Detail label={t('employee.milestoneType')}>{t(milestone.type === 'q' ? 'employee.quantifiable' : 'employee.notQuantifiable')}</Detail>
        {milestone.start_date && <Detail label={t('employee.startDate')}>{formatDate(milestone.start_date, language)}</Detail>}
        <Detail label={t('employee.deadline')}>{milestone.end_date ? formatDate(milestone.end_date, language) : t('employee.noDeadline')}</Detail>
        {milestone.type === 'q' && <Detail label={t('employee.progress')}><Progress value={milestone.quotity} label={t('employee.progress')} /></Detail>}
      </dl>

      {milestone.desc && <section className={styles.block}>
        <h3>{t('employee.description')}</h3>
        <p className={styles.description}>{milestone.desc}</p>
      </section>}

      <section className={styles.block}>
        <h3>{t('employee.assignees')}</h3>
        <ul className={styles.people}>{milestone.employees.map((employee) => {
          const name = `${employee.first_name} ${employee.last_name}`
          return <li key={employee.id}>{employee.can_view ? <Link to={`/employees/${employee.id}`}>{name}</Link> : name}</li>
        })}</ul>
      </section>
      <MilestoneDependencies key={milestone.id} milestone={milestone} onChanged={onDependenciesChanged} />
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
