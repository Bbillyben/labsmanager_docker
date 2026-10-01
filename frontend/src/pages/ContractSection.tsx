import { Plus, StickyNote } from 'lucide-react'
import { useCallback, useMemo, useRef, useState, type FormEvent } from 'react'
import {
  createContract, deleteContract, getContract, getContractOptions, getContracts, syncEmployeeEndDate, updateContract,
  type ContractOptions, type ContractRecord, type ContractScope, type ContractWrite, type EmployeeEndDateSyncOffer,
} from '../api/contracts'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { GenericNotes, type GenericNotesHandle } from '../components/GenericNotes'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { NativeSelect } from '../components/ui/native-select'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { ContractDetail } from './ContractDetail'
import { contractPercent, contractPeriod } from './contractPresentation'
import { ExpenseSection } from './ExpenseSection'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './ContractSection.module.css'

const keyFor = (scope: ContractScope) => 'hubContractId' in scope ? `hub:${scope.hubContractId}` : 'projectId' in scope ? `project:${scope.projectId}` : `employee:${scope.employeeId}`
const nameOf = (item: ContractRecord) => item.contract_type?.name ?? item.fund.display_name

export function ContractSection({ scope, onEmployeeEndDateChange }: { scope: ContractScope; onEmployeeEndDateChange?: () => void | Promise<unknown> }) {
  const { t, language } = useTranslation()
  const context = useMemo<ContractScope>(() => scope.projectId !== undefined ? { projectId: scope.projectId } : { employeeId: scope.employeeId! }, [scope.projectId, scope.employeeId])
  const key = keyFor(context)
  const load = useCallback((_id: string, signal: AbortSignal) => getContracts(context, signal), [context])
  const resource = useEmployeeResource(key, load)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<ContractRecord | 'new' | null>(null)
  const [deleting, setDeleting] = useState<ContractRecord | null>(null)
  const [syncOffer, setSyncOffer] = useState<{ contractId: number; value: EmployeeEndDateSyncOffer } | null>(null)
  const [notesFor, setNotesFor] = useState<ContractRecord | null>(null)
  const notesHandle = useRef<GenericNotesHandle | null>(null)
  const notesTrigger = useRef<HTMLElement | null>(null)
  const closingNotes = useRef(false)
  const trigger = useRef<HTMLElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const remove = useMutation()
  const sync = useMutation()
  const selected = resource.data?.items.find((item) => item.id === selectedId)
  const expenseScope = useMemo(() => selectedId === null ? null : context.projectId !== undefined
    ? { projectId: context.projectId, contractId: selectedId }
    : { employeeId: Number(context.employeeId), contractId: selectedId }, [context, selectedId])
  async function removeSelected() {
    if (!deleting) return
    const result = await remove.run(() => deleteContract(context, deleting.id))
    if (result) {
      if (selectedId === deleting.id) setSelectedId(null)
      trigger.current = section.current
      setDeleting(null)
      void resource.refresh()
    }
  }
  async function confirmEmployeeEndDate() {
    if (!syncOffer) return
    const result = await sync.run(() => syncEmployeeEndDate(context, syncOffer.contractId))
    if (result) {
      setSyncOffer(null)
      void onEmployeeEndDateChange?.()
    }
  }
  const formatDate = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  async function closeNotes() {
    if (closingNotes.current) return
    closingNotes.current = true
    try {
      if (await notesHandle.current?.savePending() !== false) {
        setNotesFor(null)
        void resource.refresh()
      }
    } finally { closingNotes.current = false }
  }
  return <section ref={section} tabIndex={-1} className={styles.section} aria-label={t('project.contracts')}>
    <div className={styles.heading}><h2>{t('project.contracts')}</h2>{resource.data?.capabilities.can_add && <Button size="sm" variant="secondary" onClick={(event) => { trigger.current = event.currentTarget; setEditing('new') }}><Plus aria-hidden="true" />{t('contracts.add')}</Button>}</div>
    {resource.loading && <p role="status">{t('contracts.loading')}</p>}
    {Boolean(resource.error) && <Alert tone="danger">{t('contracts.error')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {Boolean(resource.refreshError) && <Alert tone="warning">{t('contracts.refreshError')} <Button variant="ghost" onClick={() => void resource.refresh()}>{t('common.retry')}</Button></Alert>}
    {resource.data && (resource.data.items.length ? <div className={styles.scroll}><table className={styles.table}>
      <thead><tr><th scope="col">{t('contracts.contractType')}</th><th scope="col">{t('employee.identity')}</th><th scope="col">{t('employee.project')}</th><th scope="col">{t('employee.period')}</th><th scope="col">{t('employee.quotity')}</th><th scope="col">{t('employee.state')}</th><th scope="col"><span className="sr-only">{t('contracts.notes')}</span></th><th scope="col"><span className="sr-only">{t('list.menu')}</span></th></tr></thead>
      <tbody>{resource.data.items.map((item) => <SelectableTableRow key={item.id} rowId={item.id} selectedId={selectedId} onSelect={setSelectedId} className={styles.row} aria-label={nameOf(item)}>
        <td>{nameOf(item)}</td><td>{item.employee.first_name} {item.employee.last_name}</td><td>{item.fund.project.name}</td><td>{contractPeriod(item.start_date, item.end_date, language, t)}</td><td>{contractPercent(item.quotity, language)}</td><td>{t(item.status.code === 'effe' ? 'contracts.effective' : 'contracts.provisional')}{item.requires_follow_up ? ` · ${t('contracts.followUp')}` : ''}</td>
        <td className={styles.notes}>{(item.notes?.visible_count > 0 || item.notes?.can_add) && <Button variant="ghost" size="sm" aria-label={item.notes.visible_count > 0 ? `${t('contracts.openNotes')} · ${t(item.notes.visible_count === 1 ? 'contracts.oneNote' : 'contracts.manyNotes', { count: item.notes.visible_count })}` : t('contracts.openNotes')} onClick={(event) => { notesTrigger.current = event.currentTarget; setNotesFor(item) }}><StickyNote aria-hidden="true" />{item.notes.visible_count > 0 && <span>{item.notes.visible_count}</span>}</Button>}</td>
        <td className={styles.menu}><ItemActionMenu label={t('common.actionsFor', { name: nameOf(item) })} canChange={item.capabilities.can_change} canDelete={item.capabilities.can_delete} adminUrl={item.admin_url} onOpen={() => setSelectedId(item.id)} onTrigger={(element) => { trigger.current = element }} finalFocus={() => editing || deleting ? false : true} onEdit={() => setEditing(item)} onDelete={() => setDeleting(item)} /></td>
      </SelectableTableRow>)}</tbody>
    </table></div> : <p>{t('contracts.empty')}</p>)}
    {selected && expenseScope && <ContractSelected key={`selected:${key}:${selected.id}`} scope={context} item={selected} expenseScope={expenseScope} />}
    {notesFor && <Sheet open onOpenChange={(open) => { if (!open) void closeNotes() }}><SheetContent finalFocus={notesTrigger}>
      <SheetHeader><SheetTitle>{t('contracts.notes')}</SheetTitle><SheetDescription>{nameOf(notesFor)}</SheetDescription></SheetHeader>
      <GenericNotes ref={notesHandle} scope="contract" objectId={String(notesFor.id)} />
      <div className={styles.notesClose}><Button variant="secondary" onClick={() => void closeNotes()}>{t('common.close')}</Button></div>
    </SheetContent></Sheet>}
    {editing && <ContractFormSheet key={editing === 'new' ? `form:${key}:new` : `form:${key}:${editing.id}`} scope={context} item={editing === 'new' ? null : editing} returnFocus={trigger} onClose={() => setEditing(null)} onSaved={(item) => { setEditing(null); setSelectedId(item.id); void resource.refresh(); if (item.employee_end_date_sync?.can_update) setSyncOffer({ contractId: item.id, value: item.employee_end_date_sync }) }} />}
    {deleting && <ConfirmDialog title={t('contracts.deleteTitle')} description={t('contracts.deleteDescription', { name: nameOf(deleting) })} pending={remove.pending} error={remove.error ? <Alert tone="danger">{normalizeMutationError(remove.error).messages.join(' ') || t('contracts.saveError')}</Alert> : null} returnFocus={trigger} onCancel={() => setDeleting(null)} onConfirm={() => void removeSelected()} />}
    {syncOffer && <ConfirmDialog title={t('contracts.syncEndDateTitle')} description={t('contracts.syncEndDateDescription', { proposed: formatDate(syncOffer.value.proposed_end_date), current: syncOffer.value.current_end_date ? formatDate(syncOffer.value.current_end_date) : t('contracts.noEndDate') })} pending={sync.pending} error={sync.error ? <Alert tone="danger">{normalizeMutationError(sync.error).messages.join(' ') || t('contracts.syncEndDateError')}</Alert> : null} confirmLabel={t('contracts.syncEndDateConfirm')} cancelLabel={t('contracts.syncEndDateKeep')} returnFocus={trigger} onCancel={() => setSyncOffer(null)} onConfirm={() => void confirmEmployeeEndDate()} />}
  </section>
}

function ContractSelected({ scope, item, expenseScope }: { scope: ContractScope; item: ContractRecord; expenseScope: React.ComponentProps<typeof ExpenseSection>['scope'] }) {
  const { t } = useTranslation()
  const load = useCallback((_id: string, signal: AbortSignal) => getContract(scope, item.id, signal), [scope, item.id])
  const resource = useEmployeeResource(`${keyFor(scope)}:${item.id}`, load)
  return <div>
    {resource.loading && <p role="status">{t('contracts.detailLoading')}</p>}
    {Boolean(resource.error) && <Alert tone="danger">{t('contracts.detailError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    <ContractDetail contract={resource.data ?? item} />
    <ExpenseSection scope={expenseScope} title={t('contracts.relatedExpenses')} onFinancialChange={async () => { await resource.refresh() }} />
  </div>
}

export function ContractFormSheet({ scope, item, returnFocus, onClose, onSaved }: { scope: ContractScope; item: ContractRecord | null; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onSaved: (item: ContractRecord) => void }) {
  const { t } = useTranslation()
  const loadOptions = useCallback((_id: string, signal: AbortSignal) => getContractOptions(scope, signal), [scope])
  const options = useEmployeeResource(keyFor(scope), loadOptions)
  return <Sheet open onOpenChange={(open) => { if (!open) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(item ? 'contracts.edit' : 'contracts.add')}</SheetTitle><SheetDescription>{item ? nameOf(item) : t('project.contracts')}</SheetDescription></SheetHeader>
    {Boolean(options.error) && <Alert tone="danger">{t('contracts.optionsError')} <Button variant="ghost" onClick={options.retry}>{t('common.retry')}</Button></Alert>}
    <ContractForm scope={scope} item={item} options={options.data} onCancel={onClose} onSaved={onSaved} />
  </SheetContent></Sheet>
}

function ContractForm({ scope, item, options, onCancel, onSaved }: { scope: ContractScope; item: ContractRecord | null; options: ContractOptions | null; onCancel: () => void; onSaved: (item: ContractRecord) => void }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<ContractWrite>({
    employee_id: item?.employee.id ?? ('employeeId' in scope ? Number(scope.employeeId) : undefined),
    fund_id: item?.fund.id,
    contract_type_id: item?.contract_type?.id ?? null,
    start_date: item?.start_date ?? null,
    end_date: item?.end_date ?? null,
    quotity: item ? String(Number(item.quotity) * 100) : '100',
    status: item?.status.code ?? 'effe',
    is_active: item?.requires_follow_up ?? true,
  })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const set = <K extends keyof ContractWrite>(key: K, value: ContractWrite[K]) => setDraft((previous) => ({ ...previous, [key]: value }))
  async function save(event: FormEvent) {
    event.preventDefault()
    const payload: ContractWrite = { ...draft, quotity: (Number(draft.quotity) / 100).toFixed(3) }
    if (item) { delete payload.employee_id; delete payload.fund_id }
    const result = await mutation.run(() => item ? updateContract(scope, item.id, payload) : createContract(scope, payload))
    if (result) onSaved(result.data)
  }
  return <form className={styles.form} aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
    {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('contracts.saveError')}</Alert>}
    {'projectId' in scope && <label>{t('employee.identity')}<NativeSelect required disabled={Boolean(item) || !options} value={draft.employee_id ?? ''} onChange={(event) => set('employee_id', Number(event.target.value))}><option value="">{t('common.choose')}</option>{options?.employees.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>}
    <label>{t('contracts.fund')}<NativeSelect required disabled={Boolean(item) || !options} value={draft.fund_id ?? ''} onChange={(event) => set('fund_id', Number(event.target.value))}><option value="">{t('common.choose')}</option>{options?.funds.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>
    <label>{t('contracts.contractType')}<NativeSelect required={draft.status === 'effe'} disabled={!options} value={draft.contract_type_id ?? ''} onChange={(event) => set('contract_type_id', event.target.value ? Number(event.target.value) : null)}><option value="">{t('common.choose')}</option>{options?.contract_types.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</NativeSelect></label>
    <label>{t('projectBudgets.startDate')}<input type="date" value={draft.start_date ?? ''} onChange={(event) => set('start_date', event.target.value || null)} /></label>
    <label>{t('projectBudgets.endDate')}<input type="date" value={draft.end_date ?? ''} onChange={(event) => set('end_date', event.target.value || null)} /></label>
    <label>{t('employee.quotity')}<input required type="number" min="0" max="100" step="0.1" value={draft.quotity ?? ''} onChange={(event) => set('quotity', event.target.value)} /></label>
    <label>{t('employee.state')}<NativeSelect value={draft.status} onChange={(event) => set('status', event.target.value as 'effe' | 'prov')}><option value="effe">{t('contracts.effective')}</option><option value="prov">{t('contracts.provisional')}</option></NativeSelect></label>
    <label className={styles.check}><input type="checkbox" checked={draft.is_active ?? true} onChange={(event) => set('is_active', event.target.checked)} />{t('contracts.followUp')}</label>
    <div className={styles.actions}><Button variant="ghost" type="button" disabled={mutation.pending} onClick={onCancel}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || !options || !draft.fund_id || !draft.employee_id}>{t('common.save')}</Button></div>
  </form>
}
