import { getEmployeeBudgets, type EmployeeBudget } from '../api/employees'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './EmployeeFunding.module.css'
import { useEmployeeResource } from './useEmployeeResource'

export function EmployeeBudgets({ employeeId }: { employeeId: string }) {
  const { t } = useTranslation()
  const resource = useEmployeeResource(employeeId, getEmployeeBudgets)

  if (resource.loading) return <p className={styles.state} role="status">{t('funding.budgetsLoading')}</p>
  if (resource.error) return <div className={styles.error} role="alert"><span>{t('funding.budgetsError')}</span><Button onClick={resource.retry} size="xs" variant="ghost">{t('common.retry')}</Button></div>
  if (!resource.data?.length) return <p className={styles.state}>{t('funding.budgetsEmpty')}</p>
  return <div className={styles.budgetRows}>{resource.data.map((budget) => <BudgetRow budget={budget} key={budget.id} />)}</div>
}

function BudgetRow({ budget }: { budget: EmployeeBudget }) {
  const { language, t } = useTranslation()
  const ratio = budget.consumption_ratio === null ? null : Number(budget.consumption_ratio)
  const overrun = ratio !== null && ratio > 1
  const deficit = budget.available !== null && Number(budget.available) < 0
  const secondary = [
    budget.employee_type?.name,
    budget.contract_types.map((type) => type.name).join(', '),
    budget.quotity === null ? null : percent(Number(budget.quotity), language),
  ].filter(Boolean).join(' · ')

  return <article className={styles.budgetRow}>
    <div className={styles.budgetIdentity}>
      <strong>{budget.fund.display_name}</strong>
      <small>{budget.fund.project.name}{budget.fund.reference ? ` · ${budget.fund.reference}` : ''}</small>
      <span>{budget.cost_type?.name ?? '—'}{budget.desc ? ` · ${budget.desc}` : ''}</span>
      {secondary && <small>{secondary}</small>}
    </div>
    <dl className={styles.budgetAmounts}>
      <FinancialValue label={t('funding.budgeted')} value={budget.amount} language={language} />
      <FinancialValue label={t('funding.consumed')} value={budget.consumed} language={language} />
      <FinancialValue danger={deficit} label={t('funding.available')} value={budget.available} language={language} />
    </dl>
    <div className={`${styles.consumption} ${overrun ? styles.consumptionOverrun : ''}`}>
      {ratio === null
        ? <span className={styles.notCalculable}>{t('funding.ratioUnavailable')}</span>
        : <>{ratio >= 0 && <progress aria-label={t('funding.consumptionLabel', { name: budget.fund.display_name })} max="1" value={Math.min(ratio, 1)} />}<strong>{percent(ratio, language)}</strong></>}
    </div>
  </article>
}

function FinancialValue({ danger = false, label, language, value }: { danger?: boolean; label: string; language: string; value: string | null }) {
  return <div><dt>{label}</dt><dd className={danger ? styles.negative : undefined}>{money(value, language)}</dd></div>
}

function money(value: string | null, language: string) {
  return value === null ? '—' : new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))
}
function percent(value: number, language: string) {
  return `${new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(value * 100)} %`
}
