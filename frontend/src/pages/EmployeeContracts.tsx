import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { getEmployeeContracts, type EmployeeContract, type EmployeeContractTemporalState } from '../api/employees'
import { getDjangoUrl } from '../config/django'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { StatusBadge } from '../ui/StatusBadge'
import { ContractDetailSheet } from './ContractDetailSheet'
import { useEmployeeDetail } from './employeeDetailContext'
import styles from './EmployeeContracts.module.css'
import { useEmployeeResource } from './useEmployeeResource'

const groups: Array<{ state: EmployeeContractTemporalState; title: TranslationKey }> = [
  { state: 'current', title: 'contracts.current' },
  { state: 'future', title: 'contracts.upcoming' },
]

export function EmployeeContracts() {
  const { employeeId } = useEmployeeDetail()
  const { t } = useTranslation()
  const resource = useEmployeeResource(employeeId, getEmployeeContracts)
  const [selected, setSelected] = useState<EmployeeContract | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)

  if (resource.loading) return <p className={styles.state} role="status">{t('contracts.loading')}</p>
  if (resource.error) return <div className={styles.error} role="alert"><span>{t('contracts.error')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>
  if (!resource.data?.length) return <p className={styles.state}>{t('contracts.empty')}</p>

  const history = resource.data.filter((contract) => contract.temporal_state === 'past')
  return <>
    <div className={styles.groups}>
      {groups.map((group) => <ContractGroup
        contracts={resource.data!.filter((contract) => contract.temporal_state === group.state)}
        key={group.state}
        onOpen={setSelected}
        title={t(group.title)}
      />)}
      {history.length > 0 && <section className={styles.group}>
        <h2><button aria-expanded={historyOpen} onClick={() => setHistoryOpen((open) => !open)} type="button">
          <span>{t('contracts.history')} <strong>· {history.length}</strong></span>
          {historyOpen ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        </button></h2>
        {historyOpen && <div className={styles.rows}>{history.map((contract) => <ContractRow contract={contract} key={contract.id} onOpen={() => setSelected(contract)} />)}</div>}
      </section>}
    </div>
    <ContractDetailSheet contract={selected} employeeId={employeeId} onClose={() => setSelected(null)} />
  </>
}

function ContractGroup({ contracts, onOpen, title }: { contracts: EmployeeContract[]; onOpen: (contract: EmployeeContract) => void; title: string }) {
  if (!contracts.length) return null
  return <section className={styles.group}>
    <h2>{title} <strong>· {contracts.length}</strong></h2>
    <div className={styles.rows}>{contracts.map((contract) => <ContractRow contract={contract} key={contract.id} onOpen={() => onOpen(contract)} />)}</div>
  </section>
}

function ContractRow({ contract, onOpen }: { contract: EmployeeContract; onOpen: () => void }) {
  const { language, t } = useTranslation()
  const institution = contract.fund.institution
  return <article className={styles.row}>
    <button aria-label={t('contracts.open', { name: contract.contract_type?.name ?? contract.fund.display_name })} className={styles.open} onClick={onOpen} type="button">
      <span className={styles.identity}>
        <strong>{contract.contract_type?.name ?? contract.fund.display_name}</strong>
        <small>{contract.fund.reference || contract.fund.project.name}</small>
      </span>
      <span className={styles.period}>{period(contract.start_date, contract.end_date, language, t)}</span>
      <span className={styles.quotity}>{percent(contract.quotity, language)}</span>
      <StatusBadge>{t(contract.status.code === 'effe' ? 'contracts.effective' : 'contracts.provisional')}</StatusBadge>
      {contract.requires_follow_up && <StatusBadge tone="warning">{t('contracts.followUp')}</StatusBadge>}
    </button>
    <div className={styles.institution}>
      <span>{t('contracts.institution')}</span>
      {institution.can_view && institution.url
        ? <a href={getDjangoUrl(institution.url)}>{institution.name}</a>
        : <strong>{institution.name}</strong>}
    </div>
  </article>
}

type Translator = ReturnType<typeof useTranslation>['t']
function period(start: string | null, end: string | null, language: string, t: Translator) {
  const format = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  if (start && end) return t('employee.fromTo', { start: format(start), end: format(end) })
  if (start) return t('employee.since', { date: format(start) })
  if (end) return t('employee.until', { date: format(end) })
  return t('contracts.openPeriod')
}
function percent(value: string, language: string) { return `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(Number(value) * 100)} %` }
