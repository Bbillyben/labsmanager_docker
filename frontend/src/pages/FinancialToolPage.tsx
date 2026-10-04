import { Download, FileSignature } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getFinancialList, getFinancialOptions, getFundItemContracts, financialDefaultSort, financialQuery, type BudgetRow, type ExpenseRow, type FinancialContract, type FinancialList, type FinancialOptions, type FinancialRow, type FundItemRow, type Relation } from '../api/financialTools'
import { ListExportDialog } from '../components/ListExportDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { financialFilters, type FinancialKind } from '../config/financialFilters'
import { financialFilterSources } from '../config/financialFilterSources'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { projectFilterSources } from '../config/projectFilterSources'
import { FilterBar } from '../filters/FilterBar'
import type { FilterOption } from '../filters/types'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { LoadingState } from '../components/LoadingState'
import { PageHeader } from '../ui/PageHeader'
import { BudgetReadOnlyDetails } from './ProjectBudgetsPanel'
import { ExpenseReadOnlyDetails } from './ExpenseSection'
import styles from './EmployeeListPage.module.css'

const sources = { ...employeeFilterSources, ...projectFilterSources, ...financialFilterSources }
const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'
const moneyLabel = (value: string | null, language: string) => value === null ? '—' : new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))
const percentLabel = (value: string | null, language: string) => value === null ? '—' : new Intl.NumberFormat(language, { style: 'percent', maximumFractionDigits: 1 }).format(Number(value))

export function FinancialToolPage({ kind }: { kind: FinancialKind }) {
  const { t, language } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const canonical = financialQuery(kind, query)
  const [resultState, setResultState] = useState<{ key: string; data: FinancialList<FinancialRow> } | null>(null)
  const [options, setOptions] = useState<FinancialOptions | null>(null)
  const [error, setError] = useState(false)
  const [optionsError, setOptionsError] = useState(false)
  const [revision, setRevision] = useState(0)
  const [selection, setSelection] = useState<{ key: string; id: number } | null>(null)
  const [contractsFor, setContractsFor] = useState<FundItemRow | null>(null)
  const [contracts, setContracts] = useState<FinancialContract[] | null>(null)
  const [contractsError, setContractsError] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const exportTrigger = useRef<HTMLButtonElement | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const title = t(kind === 'fund-items' ? 'financial.fundItems' : kind === 'budgets' ? 'financial.budgets' : 'financial.expenses')
  const result = resultState?.key === `${kind}:${canonical}` ? resultState.data : null
  const selectedId = selection?.key === `${kind}:${canonical}` ? selection.id : null
  const setSelectedId = (id: number | null) => setSelection(id === null ? null : { key: `${kind}:${canonical}`, id })
  const ordering = query.get('ordering') ?? financialDefaultSort[kind]
  const pageLimit = Number(new URLSearchParams(canonical).get('limit')) || 25
  const offset = Number(query.get('offset')) || 0
  const selected = result?.results.find((row) => row.id === selectedId)

  useEffect(() => { if (query.toString() !== canonical) setQuery(canonical, { replace: true }) }, [canonical, query, setQuery])
  useEffect(() => {
    const controller = new AbortController()
    getFinancialList<FinancialRow>(kind, canonical, controller.signal).then((data) => { if (!controller.signal.aborted) { setResultState({ key: `${kind}:${canonical}`, data }); setError(false) } }, () => { if (!controller.signal.aborted) setError(true) })
    return () => controller.abort()
  }, [kind, canonical, revision])
  useEffect(() => {
    const controller = new AbortController()
    getFinancialOptions(controller.signal).then((data) => { if (!controller.signal.aborted) { setOptions(data); setOptionsError(false) } }, () => { if (!controller.signal.aborted) setOptionsError(true) })
    return () => controller.abort()
  }, [revision])
  useEffect(() => {
    if (!contractsFor) return
    const controller = new AbortController()
    getFundItemContracts(contractsFor.id, controller.signal).then((data) => { if (!controller.signal.aborted) { setContracts(data); setContractsError(false) } }, () => { if (!controller.signal.aborted) setContractsError(true) })
    return () => controller.abort()
  }, [contractsFor])

  function update(next: URLSearchParams) { setSelectedId(null); setResultState(null); setQuery(next) }
  function change(key: string, value: string) { const next = new URLSearchParams(canonical); if (value) next.set(key, value); else next.delete(key); if (key !== 'offset') next.delete('offset'); update(next) }
  const choices: Record<string, FilterOption[]> = options ? {
    costTypes: options.cost_types.map((item) => ({ value: String(item.id), label: item.name })),
    contractTypes: options.contract_types.map((item) => ({ value: String(item.id), label: item.name })),
    employeeTypes: options.employee_types.map((item) => ({ value: String(item.id), label: item.name })),
    statuses: options.statuses.map((item) => ({ value: item.value, label: item.label })),
  } : {}
  const columns = kind === 'fund-items' ? [
    [t('employee.project'), 'fund__project__name'], [t('contracts.funder'), 'fund__funder__short_name'], [t('contracts.institution'), 'fund__institution__short_name'],
    [t('projectFunding.startDate'), 'fund__start_date'], [t('projectFunding.endDate'), 'fund__end_date'], [t('projectFunding.reference'), 'fund__ref'],
    [t('funding.costType'), 'type__name'], [t('funding.amount'), 'amount'], [t('funding.consumed'), 'expense'], [t('funding.available'), '_available'],
  ] : kind === 'budgets' ? [
    [t('employee.project'), 'fund__project__name'], [t('funding.costType'), 'cost_type__name'], [t('contracts.funder'), 'fund__funder__short_name'],
    [t('contracts.institution'), 'fund__institution__short_name'], [t('projectFunding.reference'), 'fund__ref'], [t('projectBudgets.description'), ''],
    [t('funding.amount'), 'amount'], [t('funding.available'), '_available'], [t('projectBudgets.employeeType'), 'emp_type__name'],
    [t('projectBudgets.contractType'), ''], [t('projectBudgets.employee'), 'employee__last_name'], [t('projectBudgets.quotity'), ''], [t('filters.activity'), ''],
  ] : [
    [t('expenses.reference'), 'expense_id'], [t('projectBudgets.description'), 'desc'], [t('funding.costType'), 'type__name'],
    [t('funding.amount'), 'amount'], [t('expenses.status'), 'status'], [t('expenses.date'), 'date'],
    [t('employee.project'), 'fund_item__project__name'], [t('projectFunding.reference'), 'fund_item__ref'],
    [t('contracts.funder'), ''], [t('contracts.institution'), ''],
  ]
  function link(relation: Relation, route: string) { return relation.can_view ? <Link to={route}>{relation.name}</Link> : relation.name }
  function cells(row: FinancialRow) {
    const project = link(row.fund.project, `/projects/${row.fund.project.id}`)
    const funder = link(row.fund.funder, `/organizations/funders/${row.fund.funder.id}`)
    const institution = link(row.fund.institution, `/organizations/institutions/${row.fund.institution.id}`)
    if (kind === 'fund-items') {
      const item = row as FundItemRow
      return <><td>{project}</td><td>{funder}</td><td>{institution}</td><td className={styles.date}>{dateLabel(item.fund.start_date, language)}</td><td className={styles.date}>{dateLabel(item.fund.end_date, language)}</td><td>{item.fund.ref || '—'}</td><td>{item.type.name}</td><td>{moneyLabel(item.amount, language)}</td><td>{moneyLabel(item.expense, language)}</td><td>{moneyLabel(item.available, language)}</td></>
    }
    if (kind === 'budgets') {
      const item = row as BudgetRow
      return <><td>{project}</td><td>{item.cost_type?.name ?? '—'}</td><td>{funder}</td><td>{institution}</td><td>{item.fund.ref || '—'}</td><td>{item.desc || '—'}</td><td>{moneyLabel(item.amount, language)}</td><td>{moneyLabel(item.available, language)}</td><td>{item.emp_type?.name ?? '—'}</td><td>{item.contract_types?.map((entry) => entry.name).join(', ') || '—'}</td><td>{item.employee ? item.employee.can_view ? <Link to={`/employees/${item.employee.id}`}>{item.employee.name}</Link> : item.employee.name : '—'}</td><td>{percentLabel(item.quotity, language)}</td><td>{t(item.fund.is_active ? 'common.active' : 'common.inactive')}</td></>
    }
    const item = row as ExpenseRow
    return <><td>{item.expense_id || '—'}</td><td>{item.desc || '—'}</td><td>{item.type.name}</td><td>{moneyLabel(item.amount, language)}</td><td>{t(`expenses.status.${item.status}`)}</td><td className={styles.date}>{dateLabel(item.date, language)}</td><td>{project}</td><td>{item.fund.ref || '—'}</td><td>{funder}</td><td>{institution}</td></>
  }

  return <>
    <PageHeader title={title} />
    <div className="flex justify-end"><Button ref={exportTrigger} variant="secondary" onClick={() => setExportOpen(true)}><Download aria-hidden="true" />{t('listExport.title')}</Button></div>
    <FilterBar catalogue={financialFilters(kind, t)} sources={sources} choiceOptions={choices} query={new URLSearchParams(canonical)} onChange={update} resetParameters={['offset']} />
    {optionsError && <Alert tone="danger">{t('financial.optionsError')} <Button variant="ghost" onClick={() => setRevision((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {error && <Alert tone="danger">{t('financial.loadError')} <Button variant="ghost" onClick={() => setRevision((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {!error && !result && <LoadingState message={t('common.loading')} />}
    {result && !error && <section aria-label={title}>
      <p className={styles.summary} role="status">{t('financial.count', { count: result.count })}</p>
      <div className={styles.scroll} role="region" aria-label={title} tabIndex={0}><table className={styles.table}><thead><tr>{columns.map(([label, field], index) => field ? <SortableTableHeader key={index} label={label} field={field} ordering={ordering} onSort={(next) => change('ordering', next)} /> : <th key={index} scope="col">{label}</th>)}{kind === 'fund-items' && <th scope="col">{t('financial.contracts')}</th>}<th scope="col"><span className="sr-only">{t('list.menu')}</span></th></tr></thead><tbody>
        {result.results.map((row) => <SelectableTableRow key={row.id} rowId={row.id} selectedId={selectedId} onSelect={(id) => { focus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; setSelectedId(id) }} aria-label={t('financial.openDetail')}>
          {cells(row)}
          {kind === 'fund-items' && <td>{(row as FundItemRow).contract_count !== null && <Button variant="ghost" size="sm" aria-label={t('financial.openContracts', { count: (row as FundItemRow).contract_count ?? 0 })} onClick={(event) => { focus.current = event.currentTarget; setContracts(null); setContractsError(false); setContractsFor(row as FundItemRow) }}><FileSignature aria-hidden="true" />{(row as FundItemRow).contract_count}</Button>}</td>}
          <td className={styles.actions}><span className={styles.rowMenu}><ItemActionMenu label={t('common.actionsFor', { name: String(row.id) })} canChange={false} canDelete={false} adminUrl={row.admin_url} onOpen={() => {}} onTrigger={(element) => { focus.current = element }} onEdit={() => {}} onDelete={() => {}} /></span></td>
        </SelectableTableRow>)}
      </tbody></table></div>
      {!result.count && <p>{t('financial.empty')}</p>}
      <nav className={styles.pagination} aria-label={t('financial.pagination')}><Button variant="ghost" disabled={!result.previous} onClick={() => change('offset', String(Math.max(0, offset - pageLimit)))}>{t('common.previous')}</Button><span>{t('common.pageOf', { page: Math.floor(offset / pageLimit) + 1, pages: Math.max(1, Math.ceil(result.count / pageLimit)) })}</span><Button variant="ghost" disabled={!result.next} onClick={() => change('offset', String(offset + pageLimit))}>{t('common.next')}</Button></nav>
    </section>}
    {selected && <Sheet open onOpenChange={(open) => { if (!open) setSelectedId(null) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t('financial.detail')}</SheetTitle><SheetDescription>{selected.fund.project.name}</SheetDescription></SheetHeader>
      {kind === 'budgets' ? <BudgetReadOnlyDetails kind="budget" item={{ ...(selected as BudgetRow), contract_types: (selected as BudgetRow).contract_types ?? [], fund: { id: selected.fund.project.id, name: selected.fund.ref || selected.fund.project.name } }} /> : kind === 'expenses' ? <ExpenseReadOnlyDetails item={selected as ExpenseRow} /> : <FundItemDetails item={selected as FundItemRow} />}
    </SheetContent></Sheet>}
    {contractsFor && <Sheet open onOpenChange={(open) => { if (!open) setContractsFor(null) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t('financial.contracts')}</SheetTitle><SheetDescription>{contractsFor.fund.ref || contractsFor.fund.project.name}</SheetDescription></SheetHeader>
      {contractsError && <Alert tone="danger">{t('financial.loadError')}</Alert>}
      {!contracts && !contractsError && <LoadingState message={t('common.loading')} />}
      {contracts && (contracts.length ? <div className={styles.scroll}><table className={styles.table}><thead><tr><th>{t('employee.identity')}</th><th>{t('contracts.contractType')}</th><th>{t('expenses.status')}</th><th>{t('projectBudgets.startDate')}</th><th>{t('projectBudgets.endDate')}</th><th>{t('projectBudgets.quotity')}</th></tr></thead><tbody>{contracts.map((contract) => <tr key={contract.id}><td>{contract.employee}</td><td>{contract.type ?? '—'}</td><td>{t(contract.status === 'effe' ? 'contracts.effective' : 'contracts.provisional')}</td><td>{dateLabel(contract.start_date, language)}</td><td>{dateLabel(contract.end_date, language)}</td><td>{percentLabel(contract.quotity, language)}</td></tr>)}</tbody></table></div> : <p>{t('financial.empty')}</p>)}
    </SheetContent></Sheet>}
    {exportOpen && <ListExportDialog entity={kind} listQuery={canonical} returnFocus={exportTrigger} onClose={() => setExportOpen(false)} />}
  </>
}

function FundItemDetails({ item }: { item: FundItemRow }) {
  const { t, language } = useTranslation()
  return <dl className="grid gap-3 py-4">
    <div><dt>{t('employee.project')}</dt><dd>{item.fund.project.name}</dd></div>
    <div><dt>{t('contracts.funder')}</dt><dd>{item.fund.funder.name}</dd></div>
    <div><dt>{t('contracts.institution')}</dt><dd>{item.fund.institution.name}</dd></div>
    <div><dt>{t('projectFunding.reference')}</dt><dd>{item.fund.ref || '—'}</dd></div>
    <div><dt>{t('funding.costType')}</dt><dd>{item.type.name}</dd></div>
    <div><dt>{t('projectFunding.startDate')}</dt><dd>{dateLabel(item.fund.start_date, language)}</dd></div>
    <div><dt>{t('projectFunding.endDate')}</dt><dd>{dateLabel(item.fund.end_date, language)}</dd></div>
    <div><dt>{t('funding.amount')}</dt><dd>{moneyLabel(item.amount, language)}</dd></div>
    <div><dt>{t('funding.consumed')}</dt><dd>{moneyLabel(item.expense, language)}</dd></div>
    <div><dt>{t('funding.available')}</dt><dd>{moneyLabel(item.available, language)}</dd></div>
  </dl>
}
