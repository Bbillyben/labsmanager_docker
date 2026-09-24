import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { getEmployeeContributions, type EmployeeContribution, type EmployeeContributionTemporalState } from '../api/employees'
import { PersistentCollapsibleSection } from '../components/common/PersistentCollapsibleSection'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { useEmployeeDetail } from './employeeDetailContext'
import { EmployeeContributionWorkload } from './EmployeeContributionWorkload'
import { EmployeeBudgets } from './EmployeeBudgets'
import styles from './EmployeeFunding.module.css'
import { useEmployeeResource } from './useEmployeeResource'

const groups: Array<{ state: EmployeeContributionTemporalState; title: TranslationKey }> = [
  { state: 'current', title: 'funding.current' },
  { state: 'future', title: 'funding.future' },
]

export function EmployeeFunding() {
  const { employeeId } = useEmployeeDetail()
  const { t } = useTranslation()
  const resource = useEmployeeResource(employeeId, getEmployeeContributions)
  const [historyOpen, setHistoryOpen] = useState(false)
  const history = resource.data?.filter((item) => item.temporal_state === 'past') ?? []

  return <div className={styles.root}>
    <PersistentCollapsibleSection storageKey="labsmanager:employee:funding-contributions-open" title={t('funding.contributions')}>
      <EmployeeContributionWorkload employeeId={employeeId} />
      {resource.loading && <p className={styles.state} role="status">{t('funding.loading')}</p>}
      {Boolean(resource.error) && <div className={styles.error} role="alert"><span>{t('funding.error')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
      {resource.data?.length === 0 && <p className={styles.state}>{t('funding.empty')}</p>}
      {resource.data && resource.data.length > 0 && <div className={styles.groups}>
        {groups.map((group) => <ContributionGroup
          contributions={resource.data!.filter((item) => item.temporal_state === group.state)}
          key={group.state}
          title={t(group.title)}
        />)}
        {history.length > 0 && <section className={styles.group}>
          <h3><button aria-expanded={historyOpen} onClick={() => setHistoryOpen((open) => !open)} type="button">
            <span>{t('funding.history')} <strong>· {history.length}</strong></span>
            {historyOpen ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
          </button></h3>
          {historyOpen && <div className={styles.rows}>{history.map((item) => <ContributionRow item={item} key={item.id} />)}</div>}
        </section>}
      </div>}
    </PersistentCollapsibleSection>
    <PersistentCollapsibleSection storageKey="labsmanager:employee:funding-budgets-open" title={t('funding.budgets')}>
      <EmployeeBudgets employeeId={employeeId} />
    </PersistentCollapsibleSection>
  </div>
}

function ContributionGroup({ contributions, title }: { contributions: EmployeeContribution[]; title: string }) {
  if (!contributions.length) return null
  return <section className={styles.group}>
    <h3>{title} <strong>· {contributions.length}</strong></h3>
    <div className={styles.rows}>{contributions.map((item) => <ContributionRow item={item} key={item.id} />)}</div>
  </section>
}

function ContributionRow({ item }: { item: EmployeeContribution }) {
  const { language, t } = useTranslation()
  return <article className={styles.row}>
    <div className={styles.identity}>
      <strong>{item.fund.display_name}</strong>
      <small>{item.fund.project.name}{item.fund.reference ? ` · ${item.fund.reference}` : ''}</small>
      {item.desc && <span>{item.desc}</span>}
    </div>
    <div className={styles.costType}><span>{t('funding.costType')}</span><strong>{item.cost_type?.name ?? '—'}</strong></div>
    <div className={styles.metric}><span>{t('employee.period')}</span><strong>{period(item.start_date, item.end_date, language, t)}</strong></div>
    <div className={styles.metric}><span>{t('employee.quotity')}</span><strong>{percent(item.quotity, language)}</strong></div>
    <div className={styles.metric}><span>{t('funding.amount')}</span><strong>{amount(item.amount, language)}</strong></div>
  </article>
}

type Translator = ReturnType<typeof useTranslation>['t']
function period(start: string | null, end: string | null, language: string, t: Translator) {
  const format = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  if (start && end) return t('employee.fromTo', { start: format(start), end: format(end) })
  if (start) return t('employee.since', { date: format(start) })
  if (end) return t('employee.until', { date: format(end) })
  return t('funding.openPeriod')
}
function percent(value: string | null, language: string) { return value === null ? '—' : `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(Number(value) * 100)} %` }
function amount(value: string | null, language: string) { return value === null ? '—' : new Intl.NumberFormat(language, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value)) }
