import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Ellipsis, Plus } from 'lucide-react'
import { useTranslation, type Language } from '../i18n/i18n'
import { createExpensePoint, createFund, createFundItem, deleteExpensePoint, deleteFund, deleteFundItem, getFundDetail, getFundingOptions, getProjectFunding, updateExpensePoint, updateFund, updateFundItem, type CostType, type ExpensePoint, type Fund, type FundChildWrite, type FundDetail, type FundItem, type FundingOptions, type FundWrite, type ProjectFunding } from '../api/funding'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { NativeSelect } from '../components/ui/native-select'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { LoadingState } from '../components/LoadingState'
import { useEmployeeResource } from './useEmployeeResource'
import { ExpenseSection } from './ExpenseSection'
import { useTrackRecent } from '../hooks/useTrackRecent'
import styles from './ProjectFundingPanel.module.css'

const dateLabel = (value: string | null, language: Language) => value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—'
const money = (value: string, language: Language) => new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))
const fundName = (fund: Fund) => [fund.funder.short_name, fund.ref].filter(Boolean).join(' · ')

export function ProjectFundingPanel({ projectId }: { projectId: string }) {
  const { t, language } = useTranslation()
  const resource = useEmployeeResource(projectId, getProjectFunding)
  const options = useEmployeeResource(projectId, getFundingOptions)
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const linked = window.location.hash.match(/^#fund-row-(\d+)$/)?.[1]
    return linked ? Number(linked) : null
  })
  const [detailVersion, setDetailVersion] = useState(0)
  const [editing, setEditing] = useState<Fund | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Fund | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const sectionRef = useRef<HTMLElement | null>(null)
  const [focusVersion, setFocusVersion] = useState(0)
  useEffect(() => {
    if (!focusVersion) return
    const timeout = window.setTimeout(() => sectionRef.current?.focus(), 0)
    return () => window.clearTimeout(timeout)
  }, [focusVersion])
  const data = resource.data
  const selected = data?.funds.find((fund) => fund.id === selectedId) ?? null
  useTrackRecent('fund', selectedId ?? undefined, Boolean(selected))

  async function saved(fund: Fund) {
    setEditing(null)
    setSelectedId(fund.id)
    setDetailVersion((value) => value + 1)
    await resource.refresh()
  }
  async function removed() {
    focus.current = sectionRef.current
    if (deleting?.id === selectedId) setSelectedId(null)
    setDeleting(null)
    setFocusVersion((value) => value + 1)
    await resource.refresh()
  }

  if (resource.loading) return <LoadingState message={t('projectFunding.loading')} />
  if (resource.error) return <Alert tone="danger">{t('projectFunding.loadError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  if (!data) return null

  return <section className={styles.panel} aria-label={t('projectFunding.title')}>
    {Boolean(resource.refreshError) && <Alert tone="warning">{t('projectFunding.refreshError')} <Button variant="ghost" onClick={() => void resource.refresh()}>{t('common.retry')}</Button></Alert>}
    <section ref={sectionRef} id="project-funds-section" tabIndex={-1} className={styles.section} aria-labelledby="project-funds-heading">
      <div className={styles.heading}><h2 id="project-funds-heading">{t('projectFunding.funds')}</h2>{data.capabilities.can_add && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditing('new') }}><Plus aria-hidden="true" />{t('projectFunding.addFund')}</Button>}</div>
      {data.funds.length ? <div className={styles.scroll}><table className={styles.table}><thead><tr><th>{t('projectFunding.funder')}</th><th>{t('projectFunding.institution')}</th><th>{t('projectFunding.startDate')}</th><th>{t('projectFunding.endDate')}</th><th>{t('projectFunding.reference')}</th><th>{t('funding.budgeted')}</th><th>{t('funding.consumed')}</th><th>{t('funding.available')}</th><th>{t('projectFunding.status')}</th><th><span className="sr-only">{t('list.menu')}</span></th></tr></thead><tbody>
        {data.funds.map((fund) => <SelectableTableRow key={fund.id} id={`fund-row-${fund.id}`} rowId={fund.id} selectedId={selectedId} onSelect={setSelectedId}>
          <td><strong>{fund.funder.short_name}</strong></td><td>{fund.institution.short_name}</td><td>{dateLabel(fund.start_date, language)}</td><td>{dateLabel(fund.end_date, language)}</td><td>{fund.ref || '—'}</td><td className={styles.number}>{money(fund.amount, language)}</td><td className={styles.number}>{money(fund.expense, language)}</td><td className={styles.number}>{money(fund.available, language)}</td><td>{t(fund.is_active ? 'common.active' : 'common.inactive')}</td><td className={styles.actions}><ItemActionMenu label={t('common.actionsFor', { name: fundName(fund) })} canChange={fund.capabilities.can_change} canDelete={fund.capabilities.can_delete} adminUrl={fund.admin_url} onOpen={() => setSelectedId(fund.id)} onTrigger={(trigger) => { focus.current = trigger }} finalFocus={() => editing || deleting ? false : true} onEdit={() => setEditing(fund)} onDelete={() => setDeleting(fund)} /></td>
        </SelectableTableRow>)}
      </tbody></table></div> : <p className={styles.empty}>{t('projectFunding.noFunds')}</p>}
    </section>
    {selected && <FundDetailSection key={`${selected.id}:${detailVersion}`} projectId={projectId} fund={selected} options={options.data} onFinancialChange={() => resource.refresh()} />}
    {editing && <FundSheet projectId={projectId} fund={editing === 'new' ? null : editing} projectDates={data.project_dates} options={options.data} optionsError={Boolean(options.error)} retryOptions={options.retry} returnFocus={focus} onClose={() => setEditing(null)} onSaved={(fund) => void saved(fund)} />}
    {deleting && <DeleteFundingItem title={t('projectFunding.deleteFund')} description={t('projectFunding.deleteFundDescription', { name: fundName(deleting) })} returnFocus={focus} onClose={() => setDeleting(null)} onDelete={() => deleteFund(projectId, deleting.id)} onDeleted={() => void removed()} />}
  </section>
}

function FundDetailSection({ projectId, fund, options, onFinancialChange }: { projectId: string; fund: Fund; options: FundingOptions | null; onFinancialChange: () => Promise<boolean> }) {
  const { t } = useTranslation()
  const loader = useCallback((id: string, signal: AbortSignal) => getFundDetail(projectId, Number(id), signal), [projectId])
  const detail = useEmployeeResource(String(fund.id), loader)
  async function refresh() { await detail.refresh(); await onFinancialChange() }
  if (detail.loading) return <LoadingState message={t('projectFunding.detailLoading')} />
  if (detail.error) return <Alert tone="danger">{t('projectFunding.detailError')} <Button variant="ghost" onClick={detail.retry}>{t('common.retry')}</Button></Alert>
  const data = detail.data
  if (!data) return null
  return <div className={styles.fundContent}>
    {Boolean(detail.refreshError) && <Alert tone="warning">{t('projectFunding.refreshError')} <Button variant="ghost" onClick={() => void refresh()}>{t('common.retry')}</Button></Alert>}
    <FundFinancialSummary projectId={projectId} data={data} options={options} onChanged={() => void refresh()} />
    <ExpenseSection scope={{ fundId: data.fund.id }} onFinancialChange={refresh} />
  </div>
}

type FinancialRow = { type: CostType; item?: FundItem; point?: ExpensePoint; available: string }

function financialRows(detail: FundDetail): FinancialRow[] {
  const rows = new Map<number, FinancialRow>()
  for (const item of detail.items.items) rows.set(item.type.id, { type: item.type, item, available: item.available })
  for (const point of detail.expense_points.items) {
    const row = rows.get(point.type.id)
    if (row) row.point = point
    else rows.set(point.type.id, { type: point.type, point, available: point.amount })
  }
  for (const summary of detail.summary) {
    const row = rows.get(summary.type.id)
    if (row) row.available = summary.total.available
    else rows.set(summary.type.id, { type: summary.type, available: summary.total.available })
  }
  return [...rows.values()].sort((a, b) => a.type.short_name.localeCompare(b.type.short_name) || a.type.id - b.type.id)
}

function FundFinancialSummary({ projectId, data, options, onChanged }: { projectId: string; data: FundDetail; options: FundingOptions | null; onChanged: () => void }) {
  const { t, language } = useTranslation()
  const [editing, setEditing] = useState<{ kind: 'item' | 'point'; value: FundItem | ExpensePoint | null } | null>(null)
  const [deleting, setDeleting] = useState<{ kind: 'item' | 'point'; value: FundItem | ExpensePoint } | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const sectionRef = useRef<HTMLElement | null>(null)
  const [focusVersion, setFocusVersion] = useState(0)
  useEffect(() => {
    if (!focusVersion) return
    const timeout = window.setTimeout(() => sectionRef.current?.focus(), 0)
    return () => window.clearTimeout(timeout)
  }, [focusVersion])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const rows = financialRows(data)
  const canAddItem = data.items.capabilities.can_add
  const canAddPoint = data.expense_points.capabilities.can_add
  return <section ref={sectionRef} tabIndex={-1} className={styles.section} aria-labelledby="fund-summary-heading">
    <div className={styles.heading}><h2 id="fund-summary-heading">{t('projectFunding.overview')}</h2>{(canAddItem || canAddPoint) && <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={t('projectFunding.summaryActions')} onClick={(event) => { focus.current = event.currentTarget }}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
      <DropdownMenuContent align="end" finalFocus={() => editing ? false : true}>
        {canAddItem && <DropdownMenuItem onClick={() => setEditing({ kind: 'item', value: null })}><Plus aria-hidden="true" />{t('projectFunding.addItem')}</DropdownMenuItem>}
        {canAddPoint && <DropdownMenuItem onClick={() => setEditing({ kind: 'point', value: null })}><Plus aria-hidden="true" />{t('projectFunding.addPoint')}</DropdownMenuItem>}
      </DropdownMenuContent>
    </DropdownMenu>}</div>
    <div className={styles.scroll}><table className={styles.table} aria-label={t('projectFunding.overview')}><thead>
      <tr><th rowSpan={2} scope="col">{t('funding.costType')}</th><th colSpan={3} scope="colgroup">{t('projectFunding.fundItems')}</th><th colSpan={3} scope="colgroup">{t('projectFunding.expensePoints')}</th><th rowSpan={2} scope="col">{t('funding.available')}</th></tr>
      <tr><th scope="col">{t('projectFunding.valueDate')}</th><th scope="col">{t('funding.amount')}</th><th scope="col"><span className="sr-only">{t('projectFunding.itemActionsHeader')}</span></th><th scope="col">{t('projectFunding.valueDate')}</th><th scope="col">{t('funding.amount')}</th><th scope="col"><span className="sr-only">{t('projectFunding.pointActionsHeader')}</span></th></tr>
    </thead><tbody>{rows.map((row) => <SelectableTableRow key={row.type.id} id={`fund-type-row-${row.type.id}`} rowId={row.type.id} selectedId={selectedId} onSelect={setSelectedId}>
      <th scope="row">{row.type.name}</th>
      <td>{row.item ? dateLabel(row.item.value_date, language) : '—'}</td><td className={styles.number}>{row.item ? money(row.item.amount, language) : '—'}</td><td className={styles.actions}>{row.item && <ItemActionMenu label={t('projectFunding.itemActionsFor', { name: row.type.name })} canChange={data.items.capabilities.can_change} canDelete={data.items.capabilities.can_delete} adminUrl={row.item.admin_url} onOpen={() => setSelectedId(row.type.id)} onTrigger={(trigger) => { focus.current = trigger }} finalFocus={() => editing || deleting ? false : true} onEdit={() => setEditing({ kind: 'item', value: row.item! })} onDelete={() => setDeleting({ kind: 'item', value: row.item! })} />}</td>
      <td>{row.point ? dateLabel(row.point.value_date, language) : '—'}</td><td className={styles.number}>{row.point ? money(row.point.amount, language) : '—'}</td><td className={styles.actions}>{row.point && <ItemActionMenu label={t('projectFunding.pointActionsFor', { name: row.type.name })} canChange={data.expense_points.capabilities.can_change} canDelete={data.expense_points.capabilities.can_delete} adminUrl={row.point.admin_url} onOpen={() => setSelectedId(row.type.id)} onTrigger={(trigger) => { focus.current = trigger }} finalFocus={() => editing || deleting ? false : true} onEdit={() => setEditing({ kind: 'point', value: row.point! })} onDelete={() => setDeleting({ kind: 'point', value: row.point! })} />}</td>
      <td className={styles.number}>{money(row.available, language)}</td>
    </SelectableTableRow>)}<tr className={styles.total}><th scope="row">{t('projectFunding.total')}</th><td></td><td className={styles.number}>{money(data.total.amount, language)}</td><td></td><td></td><td className={styles.number}>{money(data.total.expense, language)}</td><td></td><td className={styles.number}>{money(data.total.available, language)}</td></tr></tbody></table></div>
    {editing && <FundingChildSheet kind={editing.kind} projectId={projectId} fund={data.fund} item={editing.value} options={options} returnFocus={focus} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); onChanged() }} />}
    {deleting && <DeleteFundingItem title={t(deleting.kind === 'point' ? 'projectFunding.deletePoint' : 'projectFunding.deleteItem')} description={t('projectFunding.deleteChildDescription', { name: deleting.value.type.name })} returnFocus={focus} onClose={() => setDeleting(null)} onDelete={() => deleting.kind === 'point' ? deleteExpensePoint(projectId, data.fund.id, deleting.value.id) : deleteFundItem(projectId, data.fund.id, deleting.value.id)} onDeleted={() => { focus.current = sectionRef.current; setDeleting(null); setSelectedId(null); setFocusVersion((value) => value + 1); onChanged() }} />}
  </section>
}

function FundSheet({ projectId, fund, projectDates, options, optionsError, retryOptions, returnFocus, onClose, onSaved }: { projectId: string; fund: Fund | null; projectDates: ProjectFunding['project_dates']; options: FundingOptions | null; optionsError: boolean; retryOptions: () => void; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onSaved: (fund: Fund) => void }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<FundWrite>({ funder_id: fund?.funder.id, institution_id: fund?.institution.id, start_date: fund?.start_date ?? projectDates.start_date, end_date: fund?.end_date ?? projectDates.end_date, ref: fund?.ref ?? '', update_project_end: false })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const changedEnd = Boolean(fund && draft.end_date !== fund.end_date)
  async function save(event: FormEvent) {
    event.preventDefault()
    const value = fund ? { start_date: draft.start_date, end_date: draft.end_date, ref: draft.ref, update_project_end: changedEnd && draft.update_project_end } : draft
    const result = await mutation.run(() => fund ? updateFund(projectId, fund.id, value) : createFund(projectId, value))
    if (result) onSaved(result.data)
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}><SheetHeader><SheetTitle>{t(fund ? 'projectFunding.editFund' : 'projectFunding.addFund')}</SheetTitle><SheetDescription>{fund ? fundName(fund) : t('projectFunding.fundFormDescription')}</SheetDescription></SheetHeader><form className={styles.form} onSubmit={(event) => void save(event)} aria-busy={mutation.pending}>
    {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('projectFunding.saveError')}</Alert>}
    {optionsError && !fund && <Alert tone="danger">{t('projectFunding.optionsError')} <Button variant="ghost" onClick={retryOptions}>{t('common.retry')}</Button></Alert>}
    {fund ? <><p>{t('projectFunding.funder')}: {fund.funder.name}</p><p>{t('projectFunding.institution')}: {fund.institution.name}</p></> : <>
      <label>{t('projectFunding.funder')}<NativeSelect required value={draft.funder_id ?? ''} disabled={!options || mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, funder_id: Number(event.target.value) }))}><option value="">{t('common.choose')}</option>{options?.funders.map((entry) => <option value={entry.id} key={entry.id}>{entry.short_name} — {entry.name}</option>)}</NativeSelect></label>
      <label>{t('projectFunding.institution')}<NativeSelect required value={draft.institution_id ?? ''} disabled={!options || mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, institution_id: Number(event.target.value) }))}><option value="">{t('common.choose')}</option>{options?.institutions.map((entry) => <option value={entry.id} key={entry.id}>{entry.short_name} — {entry.name}</option>)}</NativeSelect></label>
    </>}
    <label>{t('projectFunding.reference')}<input maxLength={30} value={draft.ref} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, ref: event.target.value }))} /></label>
    <label>{t('projectFunding.startDate')}<input type="date" value={draft.start_date ?? ''} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, start_date: event.target.value || null }))} /></label>
    <label>{t('projectFunding.endDate')}<input type="date" value={draft.end_date ?? ''} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, end_date: event.target.value || null }))} /></label>
    {changedEnd && <label className={styles.check}><input type="checkbox" checked={Boolean(draft.update_project_end)} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, update_project_end: event.target.checked }))} />{t('projectFunding.updateProjectEnd')}</label>}
    <div className={styles.buttons}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!fund && !options)}>{t('common.save')}</Button></div>
  </form></SheetContent></Sheet>
}

function FundingChildSheet({ kind, projectId, fund, item, options, returnFocus, onClose, onSaved }: { kind: 'item' | 'point'; projectId: string; fund: Fund; item: FundItem | ExpensePoint | null; options: FundingOptions | null; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const today = new Date().toISOString().slice(0, 10)
  const [draft, setDraft] = useState<FundChildWrite>({ type_id: item?.type.id, amount: item?.amount ?? '', entry_date: item?.entry_date ?? today, value_date: item?.value_date ?? today })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const isPoint = kind === 'point'
  async function save(event: FormEvent) {
    event.preventDefault()
    const value = item ? { amount: draft.amount, entry_date: draft.entry_date, value_date: draft.value_date } : draft
    const result = await mutation.run(() => isPoint
      ? item ? updateExpensePoint(projectId, fund.id, item.id, value) : createExpensePoint(projectId, fund.id, value)
      : item ? updateFundItem(projectId, fund.id, item.id, value) : createFundItem(projectId, fund.id, value))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}><SheetHeader><SheetTitle>{t(isPoint ? item ? 'projectFunding.editPoint' : 'projectFunding.addPoint' : item ? 'projectFunding.editItem' : 'projectFunding.addItem')}</SheetTitle><SheetDescription>{fundName(fund)}</SheetDescription></SheetHeader><form className={styles.form} onSubmit={(event) => void save(event)} aria-busy={mutation.pending}>
    {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('projectFunding.saveError')}</Alert>}
    <label>{t('funding.costType')}{item ? <strong>{item.type.name}</strong> : <NativeSelect required disabled={!options || mutation.pending} value={draft.type_id ?? ''} onChange={(event) => setDraft((value) => ({ ...value, type_id: Number(event.target.value) }))}><option value="">{t('common.choose')}</option>{options?.cost_types.map((entry) => <option value={entry.id} key={entry.id}>{entry.short_name} — {entry.name}</option>)}</NativeSelect>}</label>
    <label>{t('funding.amount')}<input type="number" step="0.01" required value={draft.amount} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, amount: event.target.value }))} /></label>
    {isPoint && <p className={styles.hint}>{t('projectFunding.pointSignHint')}</p>}
    <label>{t('projectFunding.entryDate')}<input type="date" required value={draft.entry_date} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, entry_date: event.target.value }))} /></label>
    <label>{t('projectFunding.valueDate')}<input type="date" required value={draft.value_date} disabled={mutation.pending} onChange={(event) => setDraft((value) => ({ ...value, value_date: event.target.value }))} /></label>
    <div className={styles.buttons}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!item && !options)}>{t('common.save')}</Button></div>
  </form></SheetContent></Sheet>
}

function DeleteFundingItem({ title, description, returnFocus, onClose, onDelete, onDeleted }: { title: string; description: string; returnFocus: React.RefObject<HTMLElement | null>; onClose: () => void; onDelete: () => Promise<unknown>; onDeleted: () => void }) {
  const { t } = useTranslation()
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() { const result = await mutation.run(onDelete); if (result) onDeleted() }
  return <ConfirmDialog title={title} description={description} pending={mutation.pending} error={error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('projectFunding.deleteError')}</Alert>} onCancel={onClose} onConfirm={() => void remove()} returnFocus={returnFocus} />
}
