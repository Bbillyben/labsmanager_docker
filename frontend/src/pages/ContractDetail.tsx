import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { ContractRecord } from '../api/contracts'
import { useTranslation } from '../i18n/i18n'
import { StatusBadge } from '../ui/StatusBadge'
import { contractPercent, contractPeriod } from './contractPresentation'
import { useTrackRecent } from '../hooks/useTrackRecent'
import styles from './ContractSection.module.css'

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return <div><dt>{label}</dt><dd>{children}</dd></div>
}

function Organization({ value, kind }: { value: ContractRecord['fund']['funder']; kind: 'funders' | 'institutions' }) {
  return value.can_view ? <Link to={`/organizations/${kind}/${value.id}`}>{value.name}</Link> : value.name
}

export function ContractDetail({ contract }: { contract: ContractRecord }) {
  useTrackRecent('contract', contract.id)
  const { t, language } = useTranslation()
  const employeeName = `${contract.employee.first_name} ${contract.employee.last_name}`
  const project = contract.fund.project
  return <section className={styles.detail} aria-label={t('contracts.details')}>
    <h3>{t('contracts.details')}</h3>
    <dl className={styles.fields}>
      <Detail label={t('contracts.contractType')}>{contract.contract_type?.name ?? '—'}</Detail>
      <Detail label={t('employee.identity')}>{contract.employee.can_view ? <Link to={`/employees/${contract.employee.id}`}>{employeeName}</Link> : employeeName}</Detail>
      <Detail label={t('employee.project')}>{project.can_view ? <Link to={`/projects/${project.id}`}>{project.name}</Link> : project.name}</Detail>
      <Detail label={t('contracts.funder')}><Organization value={contract.fund.funder} kind="funders" /></Detail>
      <Detail label={t('contracts.institution')}><Organization value={contract.fund.institution} kind="institutions" /></Detail>
      <Detail label={t('contracts.fund')}>{project.can_view ? <Link to={`/projects/${project.id}/funding`}>{contract.fund.display_name}</Link> : contract.fund.display_name}</Detail>
      {contract.fund.reference && <Detail label={t('contracts.reference')}>{contract.fund.reference}</Detail>}
      <Detail label={t('employee.period')}>{contractPeriod(contract.start_date, contract.end_date, language, t)}</Detail>
      <Detail label={t('employee.quotity')}>{contractPercent(contract.quotity, language)}</Detail>
      <Detail label={t('employee.state')}>{t(contract.status.code === 'effe' ? 'contracts.effective' : 'contracts.provisional')}</Detail>
      <Detail label={t('contracts.temporalState')}>{t(contract.temporal_state === 'current' ? 'contracts.temporalCurrent' : contract.temporal_state === 'future' ? 'contracts.temporalFuture' : 'contracts.temporalPast')}</Detail>
      {contract.requires_follow_up && <Detail label={t('contracts.followUp')}><StatusBadge tone="warning">{t('contracts.followUp')}</StatusBadge></Detail>}
      {contract.total_amount !== undefined && <Detail label={t('contracts.total')}>{new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(contract.total_amount))}</Detail>}
      {contract.remain_amount !== undefined && <Detail label={t('contracts.remainingAmount')}>{new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(contract.remain_amount))}</Detail>}
      {contract.man_month !== undefined && <Detail label={t('contracts.manMonths')}>{contract.man_month}</Detail>}
    </dl>
  </section>
}
