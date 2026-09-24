import { X } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { getEmployeeContract, type EmployeeContract, type EmployeeContractDetail, type EmployeeContractOrganization } from '../api/employees'
import { getDjangoUrl } from '../config/django'
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { StatusBadge } from '../ui/StatusBadge'
import styles from './ContractDetailSheet.module.css'

type DetailState = { data: EmployeeContractDetail | null; error: unknown; key: string }

export function ContractDetailSheet({ contract, employeeId, onClose }: { contract: EmployeeContract | null; employeeId: string; onClose: () => void }) {
  const { language, t } = useTranslation()
  const [attempt, setAttempt] = useState(0)
  const key = contract ? `${employeeId}:${contract.id}:${attempt}` : ''
  const [state, setState] = useState<DetailState>({ data: null, error: null, key: '' })

  useEffect(() => {
    if (!contract) return
    const controller = new AbortController()
    getEmployeeContract(employeeId, contract.id, controller.signal).then(
      (data) => { if (!controller.signal.aborted) setState({ data, error: null, key }) },
      (error: unknown) => { if (!controller.signal.aborted) setState({ data: null, error, key }) },
    )
    return () => controller.abort()
  }, [contract, employeeId, key])

  const current = state.key === key ? state : { data: null, error: null }
  const title = contract?.contract_type?.name ?? contract?.fund.display_name ?? ''
  return <Sheet onOpenChange={(open) => { if (!open) onClose() }} open={contract !== null}>
    {contract && <SheetContent>
      <SheetClose aria-label={t('common.close')} className={styles.close}><X aria-hidden="true" /></SheetClose>
      <SheetHeader>
        <SheetTitle>{title}</SheetTitle>
        <SheetDescription>{contract.fund.institution.name} · {period(contract.start_date, contract.end_date, language, t)}</SheetDescription>
      </SheetHeader>
      {!current.data && !current.error && <p className={styles.state} role="status">{t('contracts.detailLoading')}</p>}
      {Boolean(current.error) && <div className={styles.error} role="alert"><span>{t('contracts.detailError')}</span><Button onClick={() => setAttempt((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
      {current.data && <ContractDetailContent contract={current.data} />}
    </SheetContent>}
  </Sheet>
}

function ContractDetailContent({ contract }: { contract: EmployeeContractDetail }) {
  const { language, t } = useTranslation()
  const employeeName = `${contract.employee.first_name} ${contract.employee.last_name}`
  return <>
    <dl className={styles.details}>
      {contract.contract_type && <Detail label={t('contracts.contractType')}>{contract.contract_type.name}</Detail>}
      <Detail label={t('employee.identity')}>{employeeName}</Detail>
      <Detail label={t('contracts.institution')}><OrganizationValue value={contract.fund.institution} /></Detail>
      <Detail label={t('contracts.fund')}>{contract.fund.display_name}</Detail>
      <Detail label={t('employee.project')}>{contract.fund.project.name}</Detail>
      <Detail label={t('contracts.funder')}><OrganizationValue value={contract.fund.funder} /></Detail>
      {contract.fund.reference && <Detail label={t('contracts.reference')}>{contract.fund.reference}</Detail>}
      <Detail label={t('employee.period')}>{period(contract.start_date, contract.end_date, language, t)}</Detail>
      <Detail label={t('employee.quotity')}>{percent(contract.quotity, language)}</Detail>
      <Detail label={t('employee.state')}>{t(contract.status.code === 'effe' ? 'contracts.effective' : 'contracts.provisional')}</Detail>
      {contract.requires_follow_up && <Detail label={t('contracts.followUp')}><StatusBadge tone="warning">{t('contracts.followUp')}</StatusBadge></Detail>}
    </dl>
    <section className={styles.expenses}>
      <div className={styles.expenseHeading}><h3>{t('contracts.relatedExpenses')}</h3><strong>{t('contracts.total')}: {amount(contract.expense_total, language)}</strong></div>
      {contract.expenses.length === 0
        ? <p className={styles.state}>{t('contracts.noExpenses')}</p>
        : <ul>{contract.expenses.map((expense) => <li key={expense.id}>
          <span><strong>{expense.desc || expense.type.name}</strong><small>{formatDate(expense.date, language)}{expense.desc ? ` · ${expense.type.name}` : ''}</small></span>
          <strong>{amount(expense.amount, language)}</strong>
        </li>)}</ul>}
    </section>
  </>
}

function OrganizationValue({ value }: { value: EmployeeContractOrganization }) {
  return value.can_view && value.url ? <a href={getDjangoUrl(value.url)}>{value.name}</a> : value.name
}
function Detail({ children, label }: { children: ReactNode; label: string }) { return <div><dt>{label}</dt><dd>{children}</dd></div> }
type Translator = ReturnType<typeof useTranslation>['t']
function period(start: string | null, end: string | null, language: string, t: Translator) {
  if (start && end) return t('employee.fromTo', { start: formatDate(start, language), end: formatDate(end, language) })
  if (start) return t('employee.since', { date: formatDate(start, language) })
  if (end) return t('employee.until', { date: formatDate(end, language) })
  return t('contracts.openPeriod')
}
function formatDate(value: string, language: string) { return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) }
function percent(value: string, language: string) { return `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(Number(value) * 100)} %` }
function amount(value: string, language: string) { return new Intl.NumberFormat(language, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value)) }
