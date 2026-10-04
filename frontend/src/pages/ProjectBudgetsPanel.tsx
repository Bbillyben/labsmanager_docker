import { Plus } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type FormEvent } from 'react'
import {
  createProjectBudget, deleteProjectBudget, getProjectBudgetCollection, getProjectBudgetDetail,
  getProjectBudgetOptions, updateProjectBudget,
  type BudgetBase, type BudgetKind, type BudgetOptions, type BudgetWrite,
  type ProjectBudget, type ProjectContribution,
} from '../api/projectBudgets'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { NativeSelect } from '../components/ui/native-select'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { useEmployeeResource } from './useEmployeeResource'
import { ExpenseSection } from './ExpenseSection'
import styles from './ProjectBudgetsPanel.module.css'

const money = (value: string | null, language: string) => value === null ? '—' : new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))
const date = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'
const percent = (value: string | null, language: string) => value === null ? '—' : new Intl.NumberFormat(language, { style: 'percent', maximumFractionDigits: 1 }).format(Number(value))

export function ProjectBudgetsPanel({ projectId, kind }: { projectId: string; kind: BudgetKind }) {
  return <BudgetSection projectId={projectId} kind={kind} />
}

function BudgetSection({ projectId, kind }: { projectId: string; kind: BudgetKind }) {
  const { t, language } = useTranslation()
  const load = useCallback((_id: string, signal: AbortSignal) => getProjectBudgetCollection(projectId, kind, signal), [projectId, kind])
  const loadOptions = useCallback((_id: string, signal: AbortSignal) => getProjectBudgetOptions(projectId, kind, signal), [projectId, kind])
  const resource = useEmployeeResource(`${projectId}:${kind}`, load)
  const options = useEmployeeResource(`${projectId}:${kind}:options`, loadOptions)
  const [selected, setSelected] = useState<BudgetBase | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [initialEdit, setInitialEdit] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<BudgetBase | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const remove = useMutation()
  const removeError = remove.error ? normalizeMutationError(remove.error) : null
  const label = kind === 'budget' ? 'projectBudgets.budgets' : 'projectBudgets.contributions'
  const title = t(label)
  const data = resource.data
  const selectedBudget = kind === 'budget' ? data?.items.find((item) => item.id === selectedId) : null
  const expenseScope = useMemo(() => selectedId === null ? null : { projectId, budgetId: selectedId }, [projectId, selectedId])

  function open(item: BudgetBase, target: HTMLElement) {
    focus.current = target
    setInitialEdit(false)
    setSelected(item)
  }
  async function removeSelected() {
    if (!deleting) return
    const result = await remove.run(() => deleteProjectBudget(projectId, kind, deleting.id))
    if (result) {
      focus.current = section.current
      setDeleting(null)
      setSelected(null)
      if (deleting.id === selectedId) setSelectedId(null)
      void resource.refresh()
    }
  }
  const changed = async () => { await resource.refresh() }

  return <section ref={section} tabIndex={-1} className={styles.section} aria-label={title}>
    <div className={styles.heading}><h2>{title}</h2>{data?.capabilities.can_add && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setCreating(true) }}><Plus aria-hidden="true" />{t(kind === 'budget' ? 'projectBudgets.addBudget' : 'projectBudgets.addContribution')}</Button>}</div>
    {resource.loading && <p role="status">{t('genericInfo.loading')}</p>}
    {Boolean(resource.error) && <Alert tone="danger">{t('projectBudgets.loadError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {Boolean(resource.refreshError) && <Alert tone="warning">{t('projectBudgets.refreshError')} <Button variant="ghost" onClick={() => void resource.refresh()}>{t('common.retry')}</Button></Alert>}
    {data && (data.items.length ? <div className={styles.scroll}><table className={styles.table}>
      <thead><tr><th scope="col">{t('projectBudgets.fund')}</th><th scope="col">{t('funding.costType')}</th><th scope="col">{t('projectBudgets.description')}</th><th scope="col">{t('funding.amount')}</th>
        {kind === 'budget' ? <><th scope="col">{t('funding.consumed')}</th><th scope="col">{t('funding.available')}</th></> : <><th scope="col">{t('projectBudgets.startDate')}</th><th scope="col">{t('projectBudgets.endDate')}</th></>}
        <th scope="col"><span className="sr-only">{t('list.menu')}</span></th></tr></thead>
      <tbody>{data.items.map((item) => <SelectableTableRow key={item.id} id={`project-${kind}-row-${item.id}`} rowId={item.id} selectedId={kind === 'budget' ? selectedId : null} onSelect={(id) => {
        if (kind === 'budget') setSelectedId(id)
        else if (id !== null) open(item, document.getElementById(`project-${kind}-row-${item.id}`)!)
      }} className={styles.row} aria-label={kind === 'budget' ? item.desc || item.cost_type?.name || String(item.id) : t('projectBudgets.open', { name: item.desc || item.cost_type?.name || String(item.id) })}>
        <td>{item.fund.name}</td><td>{item.cost_type?.name ?? '—'}</td><td>{item.desc || '—'}</td><td className={styles.number}>{money(item.amount, language)}</td>
        {kind === 'budget' ? <><td className={styles.number}>{money((item as ProjectBudget).expense, language)}</td><td className={styles.number}>{money((item as ProjectBudget).available, language)}</td></> : <><td>{date((item as ProjectContribution).start_date, language)}</td><td>{date((item as ProjectContribution).end_date, language)}</td></>}
        <td className={styles.menu}><ItemActionMenu label={t('common.actionsFor', { name: item.desc || item.cost_type?.name || String(item.id) })} canChange={item.capabilities.can_change} canDelete={item.capabilities.can_delete} adminUrl={item.admin_url} onOpen={() => { if (kind === 'budget') setSelectedId(item.id) }} onTrigger={(trigger) => { focus.current = trigger }} finalFocus={() => selected || deleting ? false : true} onEdit={() => { setInitialEdit(true); setSelected(item) }} onDelete={() => setDeleting(item)} /></td>
      </SelectableTableRow>)}</tbody>
    </table></div> : <p>{t(kind === 'budget' ? 'projectBudgets.noBudgets' : 'projectBudgets.noContributions')}</p>)}
    {selectedBudget && expenseScope && <div className={styles.expenses}><ExpenseSection scope={expenseScope} title={t('projectBudgets.expenses')} onFinancialChange={async () => { await resource.refresh() }} /></div>}
    {creating && <BudgetFormSheet projectId={projectId} kind={kind} item={null} options={options.data} optionsError={Boolean(options.error)} retryOptions={options.retry} returnFocus={focus} onClose={() => setCreating(false)} onSaved={() => { setCreating(false); void changed() }} />}
    {selected && <BudgetDetailSheet key={`${kind}:${selected.id}`} projectId={projectId} kind={kind} item={selected} initialEdit={initialEdit} options={options.data} optionsError={Boolean(options.error)} retryOptions={options.retry} returnFocus={focus} onClose={() => setSelected(null)} onSaved={changed} />}
    {deleting && <ConfirmDialog title={t(kind === 'budget' ? 'projectBudgets.deleteBudget' : 'projectBudgets.deleteContribution')} description={t(kind === 'budget' ? 'projectBudgets.deleteBudgetDescription' : 'projectBudgets.deleteContributionDescription', { name: deleting.desc || deleting.cost_type?.name || String(deleting.id) })} pending={remove.pending} error={removeError && <Alert tone="danger">{removeError.messages.join(' ') || t('projectBudgets.saveError')}</Alert>} returnFocus={focus} onCancel={() => setDeleting(null)} onConfirm={() => void removeSelected()} />}
  </section>
}

function BudgetDetailSheet({ projectId, kind, item, initialEdit, options, optionsError, retryOptions, returnFocus, onClose, onSaved }: {
  projectId: string; kind: BudgetKind; item: BudgetBase; initialEdit: boolean; options: BudgetOptions | null; optionsError: boolean; retryOptions: () => void; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onSaved: () => Promise<void>
}) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(initialEdit)
  const load = useCallback((_id: string, signal: AbortSignal) => getProjectBudgetDetail(projectId, kind, item.id, signal), [projectId, kind, item.id])
  const resource = useEmployeeResource(`${projectId}:${kind}:${item.id}`, load)
  const current = resource.data ?? item
  return <Sheet open onOpenChange={(open) => { if (!open) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(kind === 'budget' ? 'projectBudgets.budgetDetails' : 'projectBudgets.contributionDetails')}</SheetTitle><SheetDescription>{current.desc || current.cost_type?.name || current.fund.name}</SheetDescription></SheetHeader>
    {Boolean(resource.error) && <Alert tone="danger">{t('projectBudgets.loadError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {editing ? <BudgetForm projectId={projectId} kind={kind} item={current} options={options} optionsError={optionsError} retryOptions={retryOptions} onCancel={() => setEditing(false)} onSaved={async () => { setEditing(false); await resource.refresh(); await onSaved() }} /> : <BudgetReadOnlyDetails item={current} kind={kind} />}
  </SheetContent></Sheet>
}

export function BudgetReadOnlyDetails({ item: current, kind }: { item: BudgetBase; kind: BudgetKind }) {
  const { t, language } = useTranslation()
  return <dl className={styles.details}>
        <Detail label={t('projectBudgets.fund')}>{current.fund.name}</Detail>
        <Detail label={t('funding.costType')}>{current.cost_type?.name ?? '—'}</Detail>
        <Detail label={t('projectBudgets.description')}>{current.desc || '—'}</Detail>
        <Detail label={t('projectBudgets.employeeType')}>{current.emp_type?.name ?? '—'}</Detail>
        <Detail label={t('projectBudgets.contractType')}>{current.contract_types.map((value) => value.name).join(', ') || '—'}</Detail>
        <Detail label={t('projectBudgets.employee')}>{current.employee?.name ?? '—'}</Detail>
        <Detail label={t('projectBudgets.quotity')}>{percent(current.quotity, language)}</Detail>
        <Detail label={t('funding.amount')}>{money(current.amount, language)}</Detail>
        {kind === 'budget' ? <><Detail label={t('funding.consumed')}>{money((current as ProjectBudget).expense, language)}</Detail><Detail label={t('funding.available')}>{money((current as ProjectBudget).available, language)}</Detail></> : <><Detail label={t('projectBudgets.startDate')}>{date((current as ProjectContribution).start_date, language)}</Detail><Detail label={t('projectBudgets.endDate')}>{date((current as ProjectContribution).end_date, language)}</Detail></>}
  </dl>
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><dt>{label}</dt><dd>{children}</dd></div>
}

function BudgetFormSheet({ projectId, kind, item, options, optionsError, retryOptions, returnFocus, onClose, onSaved }: {
  projectId: string; kind: BudgetKind; item: BudgetBase | null; options: BudgetOptions | null; optionsError: boolean; retryOptions: () => void; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onSaved: () => void
}) {
  const { t } = useTranslation()
  return <Sheet open onOpenChange={(open) => { if (!open) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(kind === 'budget' ? 'projectBudgets.addBudget' : 'projectBudgets.addContribution')}</SheetTitle><SheetDescription>{t('projectBudgets.formDescription')}</SheetDescription></SheetHeader>
    <BudgetForm projectId={projectId} kind={kind} item={item} options={options} optionsError={optionsError} retryOptions={retryOptions} onCancel={onClose} onSaved={onSaved} />
  </SheetContent></Sheet>
}

function BudgetForm({ projectId, kind, item, options, optionsError, retryOptions, onCancel, onSaved }: {
  projectId: string; kind: BudgetKind; item: BudgetBase | null; options: BudgetOptions | null; optionsError: boolean; retryOptions: () => void; onCancel: () => void; onSaved: () => void
}) {
  const { t } = useTranslation()
  const contribution = item && 'start_date' in item ? item as ProjectContribution : null
  const [draft, setDraft] = useState<BudgetWrite>({
    fund_id: item?.fund.id, cost_type_id: item?.cost_type?.id,
    amount: item?.amount ?? '0.00', emp_type_id: item?.emp_type?.id ?? null,
    employee_id: item?.employee?.id ?? null, contract_type_ids: item?.contract_types.map((value) => value.id) ?? [],
    quotity: item?.quotity === null || !item ? '0' : String(Number(item.quotity) * 100),
    desc: item?.desc ?? '',
    ...(kind === 'contribution' ? { start_date: contribution?.start_date ?? null, end_date: contribution?.end_date ?? null } : {}),
  })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const set = <K extends keyof BudgetWrite>(key: K, value: BudgetWrite[K]) => setDraft((previous) => ({ ...previous, [key]: value }))
  async function save(event: FormEvent) {
    event.preventDefault()
    const payload: BudgetWrite = { ...draft, quotity: draft.quotity === null ? null : (Number(draft.quotity) / 100).toFixed(3) }
    if (item) { delete payload.fund_id; delete payload.cost_type_id }
    const result = await mutation.run(() => item ? updateProjectBudget(projectId, kind, item.id, payload) : createProjectBudget(projectId, kind, payload))
    if (result) onSaved()
  }
  return <form className={styles.form} aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
    {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('projectBudgets.saveError')}</Alert>}
    {optionsError && <Alert tone="danger">{t('projectBudgets.optionsError')} <Button variant="ghost" onClick={retryOptions}>{t('common.retry')}</Button></Alert>}
    <label>{t('projectBudgets.fund')}<NativeSelect required disabled={!options || Boolean(item)} value={draft.fund_id ?? ''} onChange={(event) => set('fund_id', Number(event.target.value))}><option value="">{t('common.choose')}</option>{options?.funds.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>
    <label>{t('funding.costType')}<NativeSelect required disabled={!options || Boolean(item)} value={draft.cost_type_id ?? ''} onChange={(event) => set('cost_type_id', Number(event.target.value))}><option value="">{t('common.choose')}</option>{options?.cost_types.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>
    <label>{t('projectBudgets.description')}<input maxLength={150} value={draft.desc ?? ''} onChange={(event) => set('desc', event.target.value)} /></label>
    <label>{t('funding.amount')}<input required type="number" step="0.01" value={draft.amount ?? ''} onChange={(event) => set('amount', event.target.value)} /></label>
    <label>{t('projectBudgets.employeeType')}<NativeSelect disabled={!options} value={draft.emp_type_id ?? ''} onChange={(event) => set('emp_type_id', event.target.value ? Number(event.target.value) : null)}><option value="">{t('common.choose')}</option>{options?.employee_types.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>
    <label>{t('projectBudgets.contractType')}<select className={styles.multi} multiple size={Math.min(4, Math.max(2, options?.contract_types.length ?? 2))} disabled={!options} value={(draft.contract_type_ids ?? []).map(String)} onChange={(event) => set('contract_type_ids', Array.from(event.target.selectedOptions, (option) => Number(option.value)))}>{options?.contract_types.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</select></label>
    <label>{t('projectBudgets.employee')}<NativeSelect disabled={!options} value={draft.employee_id ?? ''} onChange={(event) => set('employee_id', event.target.value ? Number(event.target.value) : null)}><option value="">{t('common.choose')}</option>{options?.employees.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}{item?.employee && !options?.employees.some((value) => value.id === item.employee?.id) && <option value={item.employee.id}>{item.employee.name}</option>}</NativeSelect></label>
    <label>{t('projectBudgets.quotity')}<input type="number" min="0" max="100" step="0.1" value={draft.quotity ?? ''} onChange={(event) => set('quotity', event.target.value)} /></label>
    {kind === 'contribution' && <><label>{t('projectBudgets.startDate')}<input type="date" value={draft.start_date ?? ''} onChange={(event) => set('start_date', event.target.value || null)} /></label><label>{t('projectBudgets.endDate')}<input type="date" value={draft.end_date ?? ''} onChange={(event) => set('end_date', event.target.value || null)} /></label></>}
    <div className={styles.actions}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onCancel}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || !options || (!item && (!draft.fund_id || !draft.cost_type_id))}>{t('common.save')}</Button></div>
  </form>
}
