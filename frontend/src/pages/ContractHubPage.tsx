import { Download } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getContract, getContractHub, getContractHubOptions, contractHubQuery, readContractHubParams, type ContractHubListResponse, type ContractHubOptions, type ContractRecord } from '../api/contracts'
import { ApiError, normalizeMutationError } from '../api/errors'
import { syncEmployeeEndDate } from '../api/contracts'
import { useMutation } from '../api/useMutation'
import { ListExportDialog } from '../components/ListExportDialog'
import { LoadingState } from '../components/LoadingState'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { contractFilters } from '../config/contractFilters'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { projectFilterSources } from '../config/projectFilterSources'
import { FilterBar } from '../filters/FilterBar'
import type { FilterOption } from '../filters/types'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { ContractDetail } from './ContractDetail'
import { ContractFormSheet } from './ContractSection'
import { ContractHubTable } from './ContractHubTable'
import { ExpenseSection } from './ExpenseSection'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeListPage.module.css'

const sources = { ...employeeFilterSources, ...projectFilterSources }
const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'

export function ContractHubPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const params = readContractHubParams(query)
  const canonical = contractHubQuery(params)
  const [result, setResult] = useState<ContractHubListResponse | null>(null)
  const [options, setOptions] = useState<ContractHubOptions | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [optionsError, setOptionsError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const exportTrigger = useRef<HTMLButtonElement | null>(null)
  const actionTrigger = useRef<HTMLElement | null>(null)

  useEffect(() => { if (query.toString() !== canonical) setQuery(canonical, { replace: true }) }, [query, canonical, setQuery])
  useEffect(() => {
    const controller = new AbortController()
    getContractHub(readContractHubParams(new URLSearchParams(canonical)), controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setResult(data); setError(null) } },
      (cause: unknown) => { if (!controller.signal.aborted) setError(cause) },
    )
    return () => controller.abort()
  }, [canonical, retry])
  useEffect(() => {
    const controller = new AbortController()
    getContractHubOptions(controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setOptions(data); setOptionsError(false) } },
      () => { if (!controller.signal.aborted) setOptionsError(true) },
    )
    return () => controller.abort()
  }, [retry])

  const changeQuery = useCallback((next: URLSearchParams) => {
    setSelectedId(null)
    setEditingId(null)
    setResult(null)
    setError(null)
    setQuery(next)
  }, [setQuery])
  const update = (patch: Partial<typeof params>) => changeQuery(new URLSearchParams(contractHubQuery({ ...params, offset: 0, ...patch })))
  const page = Math.floor(params.offset / params.limit) + 1
  const pages = Math.max(1, Math.ceil((result?.count ?? 0) / params.limit))
  const choiceOptions: Record<string, FilterOption[]> = options ? {
    contractTypes: options.contract_types.map((item) => ({ value: String(item.id), label: item.name })),
    contractStatuses: options.statuses.map((item) => ({ value: item.value, label: item.label })),
    funders: options.funders.map((item) => ({ value: String(item.id), label: item.short_name })),
    institutions: options.institutions.map((item) => ({ value: String(item.id), label: item.short_name })),
  } : {}

  return <>
    <PageHeader title={t('navigation.contracts')} />
    <div className="flex justify-end"><Button ref={exportTrigger} variant="secondary" onClick={() => setExportOpen(true)}><Download aria-hidden="true" />{t('listExport.title')}</Button></div>
    <FilterBar catalogue={contractFilters(t)} sources={sources} choiceOptions={choiceOptions} query={new URLSearchParams(canonical)} onChange={changeQuery} resetParameters={['offset']} />
    {optionsError && <Alert tone="danger">{t('contractHub.optionsError')} <Button variant="ghost" onClick={() => setRetry((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {error && <Alert tone="danger">{error instanceof ApiError && error.status === 403 ? t('contractHub.forbidden') : t('contractHub.loadError')} <Button variant="ghost" onClick={() => setRetry((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {!error && !result && <LoadingState message={t('contractHub.loading')} />}
    {!error && result && <section aria-label={t('navigation.contracts')}>
      <p className={styles.summary} role="status">{t('contractHub.count', { count: result.count })}</p>
      <ContractHubTable items={result.results} selectedId={selectedId} onSelect={setSelectedId} onNotesClosed={() => setRetry((value) => value + 1)} onEdit={(item) => { setSelectedId(item.id); setEditingId(item.id) }} onActionTrigger={(element) => { actionTrigger.current = element }} editingId={editingId} ordering={params.ordering} onSort={(ordering) => update({ ordering })} />
      {!result.count && <p>{t('contractHub.empty')}</p>}
      <nav className={styles.pagination} aria-label={t('contractHub.pagination')}>
        <Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: Math.max(0, params.offset - params.limit) })}>{t('common.previous')}</Button>
        <span>{t('common.pageOf', { page, pages })}</span>
        <Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: params.offset + params.limit })}>{t('common.next')}</Button>
      </nav>
    </section>}
    {selectedId !== null && <ContractHubSelected key={selectedId} id={selectedId} editing={editingId === selectedId} onCloseEdit={() => setEditingId(null)} onChanged={() => setRetry((value) => value + 1)} returnFocus={actionTrigger} />}
    {exportOpen && <ListExportDialog entity="contracts" listQuery={canonical} returnFocus={exportTrigger} onClose={() => setExportOpen(false)} />}
  </>
}

function ContractHubSelected({ id, editing, onCloseEdit, onChanged, returnFocus }: {
  id: number; editing: boolean; onCloseEdit: () => void; onChanged: () => void; returnFocus: React.RefObject<HTMLElement | null>
}) {
  const { t, language } = useTranslation()
  const scope = { hubContractId: id } as const
  const load = useCallback((_id: string, signal: AbortSignal) => getContract({ hubContractId: id }, id, signal), [id])
  const detail = useEmployeeResource(String(id), load)
  const sync = useMutation()
  const [offer, setOffer] = useState<ContractRecord['employee_end_date_sync']>(null)
  const formatDate = (value: string) => dateLabel(value, language)
  async function applySync() {
    const result = await sync.run(() => syncEmployeeEndDate(scope, id))
    if (result) setOffer(null)
  }
  return <section aria-label={t('contracts.details')}>
    {detail.loading && <LoadingState message={t('contracts.detailLoading')} />}
    {Boolean(detail.error) && <Alert tone="danger">{t('contracts.detailError')} <Button variant="ghost" onClick={detail.retry}>{t('common.retry')}</Button></Alert>}
    {Boolean(detail.refreshError) && <Alert tone="warning">{t('contracts.refreshError')} <Button variant="ghost" onClick={() => void detail.refresh()}>{t('common.retry')}</Button></Alert>}
    {detail.data && <><ContractDetail contract={detail.data} /><ExpenseSection scope={scope} title={t('contracts.relatedExpenses')} onFinancialChange={() => { void detail.refresh(); onChanged() }} /></>}
    {editing && detail.data && <ContractFormSheet scope={scope} item={detail.data} returnFocus={returnFocus} onClose={onCloseEdit} onSaved={(saved) => { detail.updateData(() => saved); onCloseEdit(); onChanged(); void detail.refresh(); if (saved.employee_end_date_sync?.can_update) setOffer(saved.employee_end_date_sync) }} />}
    {offer && <ConfirmDialog title={t('contracts.syncEndDateTitle')} description={t('contracts.syncEndDateDescription', { proposed: formatDate(offer.proposed_end_date), current: offer.current_end_date ? formatDate(offer.current_end_date) : t('contracts.noEndDate') })} pending={sync.pending} error={sync.error ? <Alert tone="danger">{normalizeMutationError(sync.error).messages.join(' ') || t('contracts.syncEndDateError')}</Alert> : null} confirmLabel={t('contracts.syncEndDateConfirm')} cancelLabel={t('contracts.syncEndDateKeep')} returnFocus={returnFocus} onCancel={() => setOffer(null)} onConfirm={() => void applySync()} />}
  </section>
}
