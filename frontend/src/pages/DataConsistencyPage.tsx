import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { acceptConsistencyBatch, acceptConsistencyIssue, consistencyIssueId, correctConsistencyBatch, correctConsistencyIssue, DATA_CONSISTENCY_CHANGED, getConsistencyIssues, getConsistencySummary, reopenConsistencyIssue, type ConsistencyBatchResult, type ConsistencyCorrectionResult, type ConsistencyIssue, type ConsistencyIssues, type ConsistencySummary } from '../api/dataConsistency'
import { normalizeMutationError } from '../api/errors'
import { getEmployee, type EmployeeDetail } from '../api/employees'
import { getFundDetail, type Fund } from '../api/funding'
import { getProject, type ProjectOverview } from '../api/projects'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { CheckboxRow } from '../components/CheckboxRow'
import { LoadingState } from '../components/LoadingState'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Textarea } from '../components/ui/textarea'
import { translations, useTranslation, type TranslationKey } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { ParticipantSheet } from './ProjectParticipantBlock'

type Status = 'active' | 'accepted'
const LIMIT = 25
const PARTICIPANT_RULE = 'contract_employee_not_project_participant'
const CONTRACT_DATES_RULE = 'contract_outside_project_dates'
const FUND_DATES_RULE = 'fund_outside_project_dates'
const EMPLOYEE_DATES_RULE = 'contract_outside_employee_dates'
const MILESTONE_DATES_RULE = 'milestone_outside_project_dates'
const TASK_DATES_RULE = 'task_outside_project_dates'
const CONTRACT_FUND_DATES_RULE = 'contract_outside_fund_dates'
const EXPENSE_FUND_DATES_RULE = 'expense_outside_fund_dates'
const PROJECT_LEADER_RULE = 'project_without_leader'

function extendedDates(parentStart: string | null, parentEnd: string | null, issue: ConsistencyIssue) {
  const childStart = issue.child_start_date ?? null
  const childEnd = issue.child_end_date ?? null
  return {
    start_date: parentStart === null || childStart === null ? null : parentStart < childStart ? parentStart : childStart,
    end_date: parentEnd === null || childEnd === null ? null : parentEnd > childEnd ? parentEnd : childEnd,
  }
}

function parentKind(issue: ConsistencyIssue) {
  if (issue.rule_key === EMPLOYEE_DATES_RULE) return 'employee'
  if (issue.rule_key === CONTRACT_FUND_DATES_RULE || issue.rule_key === EXPENSE_FUND_DATES_RULE) return 'fund'
  return 'project'
}

const issueId = consistencyIssueId

export function DataConsistencyPage() {
  const { t, language } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [status, setStatus] = useState<Status>(searchParams.get('status') === 'accepted' ? 'accepted' : 'active')
  const [ruleKey, setRuleKey] = useState(searchParams.get('rule') || PARTICIPANT_RULE)
  const [offset, setOffset] = useState(() => {
    const value = Number(searchParams.get('offset'))
    return Number.isSafeInteger(value) && value >= 0 && value % LIMIT === 0 ? value : 0
  })
  const [revision, setRevision] = useState(0)
  const [summary, setSummary] = useState<ConsistencySummary | null>(null)
  const [result, setResult] = useState<ConsistencyIssues | null>(null)
  const [participantProject, setParticipantProject] = useState<ProjectOverview | null>(null)
  const [employees, setEmployees] = useState<Record<number, EmployeeDetail>>({})
  const [funds, setFunds] = useState<Record<number, Fund>>({})
  const [participantIssue, setParticipantIssue] = useState<ConsistencyIssue | null>(null)
  const [dateIssue, setDateIssue] = useState<ConsistencyIssue | null>(null)
  const [genericIssue, setGenericIssue] = useState<ConsistencyIssue | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [summaryError, setSummaryError] = useState(false)
  const [selected, setSelected] = useState<ConsistencyIssue | null>(null)
  const [reason, setReason] = useState('')
  const [pending, setPending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [overviewFilter, setOverviewFilter] = useState<'all' | 'issues'>('all')
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedIssues, setSelectedIssues] = useState<Map<number, ConsistencyIssue>>(new Map())
  const [allMatching, setAllMatching] = useState(false)
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set())
  const [bulkReason, setBulkReason] = useState('')
  const [bulkConfirm, setBulkConfirm] = useState(false)
  const [bulkAction, setBulkAction] = useState<'accept' | 'correct'>('accept')
  const [bulkPending, setBulkPending] = useState(false)
  const [bulkError, setBulkError] = useState<string | null>(null)
  const [bulkReport, setBulkReport] = useState<{ action: 'accept'; data: ConsistencyBatchResult } | { action: 'correct'; data: ConsistencyCorrectionResult } | null>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  const scrollToDetail = useRef(false)

  const remember = useCallback((next: { status?: Status; rule?: string; offset?: number }) => {
    setSearchParams((current) => {
      const params = new URLSearchParams(current)
      if (next.status) params.set('status', next.status)
      if (next.rule) params.set('rule', next.rule)
      if (next.offset !== undefined) {
        if (next.offset) params.set('offset', String(next.offset))
        else params.delete('offset')
      }
      return params
    }, { replace: true })
  }, [setSearchParams])

  const clearSelection = () => {
    setSelectedIssues(new Map()); setAllMatching(false); setExcludedIds(new Set())
    setBulkReason(''); setBulkConfirm(false); setBulkError(null)
  }

  useEffect(() => {
    const controller = new AbortController()
    getConsistencySummary(controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setSummary(data); setSummaryError(false) } },
      () => { if (!controller.signal.aborted) setSummaryError(true) },
    )
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    if (summary?.rules.length && !summary.rules.some((rule) => rule.rule_key === ruleKey)) {
      const fallback = summary.rules[0].rule_key
      setRuleKey(fallback); setOffset(0); remember({ rule: fallback, offset: 0 })
    }
  }, [summary, ruleKey, remember])

  useEffect(() => {
    const controller = new AbortController()
    setResult(null)
    getConsistencyIssues(status, offset, LIMIT, controller.signal, ruleKey).then(
      (data) => { if (!controller.signal.aborted) { setResult(data); setLoadError(false) } },
      () => { if (!controller.signal.aborted) setLoadError(true) },
    )
    return () => controller.abort()
  }, [status, ruleKey, offset, revision])

  useEffect(() => {
    if (result && scrollToDetail.current) {
      scrollToDetail.current = false
      document.getElementById('consistency-detail')?.scrollIntoView?.({ block: 'start' })
    }
  }, [result])

  useEffect(() => {
    const controller = new AbortController()
    setEmployees({}); setFunds({})
    if (status === 'active' && result) {
      const employeeIds = [...new Set(result.results.filter((issue) => parentKind(issue) === 'employee').map((issue) => issue.employee_id).filter((id): id is number => id !== undefined))]
      const fundIssues = result.results.filter((issue) => parentKind(issue) === 'fund' && issue.fund_id && issue.project_id !== null)
      void Promise.all(employeeIds.map(async (id) => {
        try { return [id, await getEmployee(String(id), controller.signal)] as const }
        catch { return null }
      })).then((entries) => {
        if (!controller.signal.aborted) setEmployees(Object.fromEntries(entries.filter((entry): entry is readonly [number, EmployeeDetail] => entry !== null)))
      })
      void Promise.all(fundIssues.map(async (issue) => {
        try { return [issue.fund_id!, (await getFundDetail(String(issue.project_id), issue.fund_id!, controller.signal)).fund] as const }
        catch { return null }
      })).then((entries) => {
        if (!controller.signal.aborted) setFunds(Object.fromEntries(entries.filter((entry): entry is readonly [number, Fund] => entry !== null)))
      })
    }
    return () => controller.abort()
  }, [result, status])

  const refresh = () => {
    clearSelection(); setSelectionMode(false)
    setOffset(0)
    remember({ offset: 0 })
    setRevision((value) => value + 1)
    window.dispatchEvent(new Event(DATA_CONSISTENCY_CHANGED))
  }

  const accept = async () => {
    if (!selected) return
    setPending(true); setActionError(null)
    try {
      await acceptConsistencyIssue(selected, reason)
      setSelected(null); setReason(''); refresh()
    } catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const reopen = async (issue: ConsistencyIssue) => {
    if (!issue.exception) return
    setPending(true); setActionError(null)
    try { await reopenConsistencyIssue(issue.exception.id); refresh() }
    catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const dateParent = (issue: ConsistencyIssue) => {
    const kind = parentKind(issue)
    if (kind === 'employee') {
      const employee = employees[issue.employee_id ?? -1]
      return employee && { kind, id: employee.id, start: employee.entry_date, end: employee.exit_date, canChange: Boolean(employee.capabilities?.can_change) }
    }
    if (kind === 'fund') {
      const fund = funds[issue.fund_id ?? -1]
      return fund && { kind, id: fund.id, start: fund.start_date, end: fund.end_date, canChange: fund.capabilities.can_change }
    }
    if (issue.project_id === null) return undefined
    return { kind, id: issue.project_id, start: issue.parent_start_date ?? null, end: issue.parent_end_date ?? null, canChange: issue.correction_action === 'extend_dates' }
  }

  const openParticipant = async (issue: ConsistencyIssue) => {
    if (!issue.project_id || !issue.can_add_participant) return
    setPending(true); setActionError(null)
    try {
      const project = await getProject(String(issue.project_id), new AbortController().signal)
      if (!project.participants.capabilities.can_add) return
      setParticipantProject(project); setParticipantIssue(issue)
    } catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const extendParent = async () => {
    if (!dateIssue) return
    const parent = dateParent(dateIssue)
    if (!parent?.canChange) return
    setPending(true); setActionError(null)
    try {
      await correctConsistencyIssue(dateIssue)
      setDateIssue(null)
      refresh()
    } catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const applyGenericCorrection = async () => {
    if (!genericIssue) return
    setPending(true); setActionError(null)
    try {
      await correctConsistencyIssue(genericIssue)
      setGenericIssue(null)
      refresh()
    } catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const chooseStatus = (next: Status) => { clearSelection(); setSelectionMode(false); setBulkReport(null); setResult(null); setStatus(next); setOffset(0); remember({ status: next, offset: 0 }); setActionError(null) }
  const chooseRule = (next: string) => { clearSelection(); setSelectionMode(false); setBulkReport(null); setResult(null); setRuleKey(next); setOffset(0); remember({ rule: next, offset: 0 }); setActionError(null) }
  const date = (value: string) => new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
  const dateLabel = (value: string | null) => value ? new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`)) : t('dataConsistency.openDate')
  const ruleLabel = (key: string) => {
    switch (key) {
      case CONTRACT_DATES_RULE: return t('dataConsistency.rule.contract_outside_project_dates')
      case FUND_DATES_RULE: return t('dataConsistency.rule.fund_outside_project_dates')
      case EMPLOYEE_DATES_RULE: return t('dataConsistency.rule.contract_outside_employee_dates')
      case MILESTONE_DATES_RULE: return t('dataConsistency.rule.milestone_outside_project_dates')
      case TASK_DATES_RULE: return t('dataConsistency.rule.task_outside_project_dates')
      case CONTRACT_FUND_DATES_RULE: return t('dataConsistency.rule.contract_outside_fund_dates')
      case EXPENSE_FUND_DATES_RULE: return t('dataConsistency.rule.expense_outside_fund_dates')
      case PROJECT_LEADER_RULE: return t('dataConsistency.rule.project_without_leader')
      case PARTICIPANT_RULE: return t('dataConsistency.rule.contract_employee_not_project_participant')
      default: {
        const translation = `dataConsistency.rule.${key}`
        return translation in translations.fr ? t(translation as TranslationKey) : summary?.rules.find((rule) => rule.rule_key === key)?.label || key
      }
    }
  }
  const categoryLabel = (key: string) => {
    switch (key) {
      case 'contracts': return t('dataConsistency.contracts')
      case 'funds': return t('dataConsistency.funds')
      case 'planning': return t('dataConsistency.planning')
      case 'expenses': return t('dataConsistency.expenses')
      case 'projects': return t('dataConsistency.projects')
      case 'employees': return t('dataConsistency.employees')
      case 'teams': return t('dataConsistency.teams')
      default: return key
    }
  }
  const actionLabel = (issue: ConsistencyIssue) => {
    switch (issue.rule_key) {
      case CONTRACT_DATES_RULE: return t('dataConsistency.extendContract')
      case FUND_DATES_RULE: return t('dataConsistency.extendFund')
      case EMPLOYEE_DATES_RULE: return t('dataConsistency.extendEmployee')
      case MILESTONE_DATES_RULE: return t('dataConsistency.extendMilestone')
      case TASK_DATES_RULE: return t('dataConsistency.extendTask')
      case CONTRACT_FUND_DATES_RULE: return t('dataConsistency.extendContractFund')
      default: return t('dataConsistency.extendExpenseFund')
    }
  }
  const objectLabel = (issue: ConsistencyIssue) => {
    if (issue.object_label) return issue.object_label
    if (issue.expense_id) return `${t('dataConsistency.expense')} #${issue.expense_id}`
    if (issue.milestone_id) return `${t(issue.rule_key === TASK_DATES_RULE ? 'dataConsistency.task' : 'dataConsistency.milestone')} #${issue.milestone_id}`
    if (issue.contract_id) return `${t('dataConsistency.contract')} #${issue.contract_id}`
    if (issue.fund_id) return `${t('dataConsistency.fund')} #${issue.fund_id}`
    return `${t('dataConsistency.project')} #${issue.project_id}`
  }
  const genericActionLabel = (key: string) => {
    const translation = `dataConsistency.action.${key}`
    return translation in translations.fr ? t(translation as TranslationKey) : t('dataConsistency.correctAction')
  }
  const previewParent = dateIssue && dateParent(dateIssue)
  const previewDates = previewParent && dateIssue ? extendedDates(previewParent.start, previewParent.end, dateIssue) : null
  const selectedCount = summary?.rules.find((rule) => rule.rule_key === ruleKey)
  const currentTotal = status === 'active' ? summary?.total ?? 0 : summary?.accepted_total ?? 0
  const rulesWithIssues = summary?.rules.filter((rule) => (status === 'active' ? rule.count : rule.accepted_count) > 0).length ?? 0
  const visibleRules = summary?.rules.filter((rule) => overviewFilter === 'all' || (status === 'active' ? rule.count : rule.accepted_count) > 0) ?? []
  const selectableCount = allMatching ? Math.max(0, (result?.count ?? 0) - excludedIds.size) : selectedIssues.size
  const canCorrect = Boolean(selectedCount?.correction_action)
  const participantBatch = selectedCount?.correction_action === 'add_participants'
  const lifecycleBatch = selectedCount?.correction_action === 'apply_correction'
  const correctionLabel = participantBatch ? 'dataConsistency.addParticipantsSelected' : lifecycleBatch ? 'dataConsistency.applySelected' : 'dataConsistency.correctSelected'
  const canSelect = status === 'active' && (Boolean(summary?.capabilities.can_accept) || canCorrect)
  const toggleIssue = (issue: ConsistencyIssue) => {
    const id = issueId(issue)
    if (allMatching) {
      setExcludedIds((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next })
    } else {
      setSelectedIssues((current) => { const next = new Map(current); if (next.has(id)) next.delete(id); else next.set(id, issue); return next })
    }
  }
  const selectVisible = () => {
    if (!result) return
    if (allMatching) {
      setExcludedIds((current) => { const next = new Set(current); result.results.forEach((issue) => next.delete(issueId(issue))); return next })
    } else {
      setSelectedIssues((current) => { const next = new Map(current); result.results.forEach((issue) => next.set(issueId(issue), issue)); return next })
    }
  }
  const runBatch = async () => {
    if (!canSelect || selectableCount === 0 || (bulkAction === 'accept' && !summary?.capabilities.can_accept) || (bulkAction === 'correct' && !canCorrect)) return
    setBulkPending(true); setBulkError(null)
    try {
      const selection = allMatching
        ? { mode: 'all' as const, excluded_ids: [...excludedIds], selected_count: selectableCount }
        : { mode: 'selected' as const, issues: [...selectedIssues.values()].map((issue) => ({ id: issueId(issue), project_id: issue.project_id, ...(issue.employee_id && { employee_id: issue.employee_id }), ...(issue.fund_id && { fund_id: issue.fund_id }), ...(issue.team_id && { team_id: issue.team_id }) })), selected_count: selectableCount }
      if (bulkAction === 'correct') setBulkReport({ action: 'correct', data: await correctConsistencyBatch(ruleKey, selection) })
      else setBulkReport({ action: 'accept', data: await acceptConsistencyBatch(ruleKey, selection, bulkReason) })
      refresh()
    } catch (error) { setBulkError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setBulkPending(false) }
  }

  return <>
    <PageHeader title={t('dataConsistency.title')} />
    {summary ? <section className="grid gap-3" aria-label={t('dataConsistency.overview')}>
      <div className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg border border-border px-4 py-3 text-sm">
        <span><strong>{currentTotal}</strong> {t('dataConsistency.occurrences')}</span>
        <span><strong>{rulesWithIssues}</strong> {t('dataConsistency.rulesWithIssues')}</span>
        <span><strong>{summary.rules.length}</strong> {t('dataConsistency.availableRules')}</span>
      </div>
      <p className="text-sm text-muted-foreground">{t('dataConsistency.occurrencesHint')}</p>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t('dataConsistency.overview')}</h2>
        <div className="flex gap-2" role="group" aria-label={t('dataConsistency.overviewFilter')}>
          <Button size="sm" variant={overviewFilter === 'all' ? 'default' : 'secondary'} aria-pressed={overviewFilter === 'all'} onClick={() => setOverviewFilter('all')}>{t('dataConsistency.filterAll')}</Button>
          <Button size="sm" variant={overviewFilter === 'issues' ? 'default' : 'secondary'} aria-pressed={overviewFilter === 'issues'} onClick={() => setOverviewFilter('issues')}>{t('dataConsistency.filterIssues')}</Button>
        </div>
      </div>
      {visibleRules.length ? <ul className="divide-y rounded-lg border border-border mb-4" >
        {visibleRules.map((rule) => <li key={rule.rule_key} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div className="min-w-0"><p className="font-medium">{ruleLabel(rule.rule_key)}</p><p className="text-sm text-muted-foreground">{categoryLabel(rule.category)}</p></div>
          <div className="flex items-center gap-3"><span className="text-sm tabular-nums">{status === 'active' ? rule.count : rule.accepted_count}</span><Button size="sm" variant={ruleKey === rule.rule_key ? 'default' : 'ghost'} aria-label={t('dataConsistency.viewRuleDetails', { rule: ruleLabel(rule.rule_key) })} aria-pressed={ruleKey === rule.rule_key} onClick={() => { scrollToDetail.current = true; chooseRule(rule.rule_key) }}>{t('dataConsistency.viewDetails')}</Button></div>
        </li>)}</ul> : <p>{t('dataConsistency.noMatchingRules')}</p>}
    </section> : !summaryError && <LoadingState message={t('common.loading')} />}
    {summaryError && <Alert tone="danger">{t('dataConsistency.loadError')} <Button variant="ghost" onClick={refresh}>{t('common.retry')}</Button></Alert>}
    <div className="flex flex-wrap gap-2 mb-2" role="group" aria-label={t('dataConsistency.status')}>
      <Button variant={status === 'active' ? 'default' : 'secondary'} aria-pressed={status === 'active'} onClick={() => chooseStatus('active')}>{t('dataConsistency.active')} {summary && `(${selectedCount?.count ?? summary.total})`}</Button>
      <Button variant={status === 'accepted' ? 'default' : 'secondary'} aria-pressed={status === 'accepted'} onClick={() => chooseStatus('accepted')}>{t('dataConsistency.accepted')} {summary && `(${selectedCount?.accepted_count ?? summary.accepted_total})`}</Button>
    </div>
    {summary && summary.rules.length > 1 && <label className="flex items-center gap-2 mb-2">{t('dataConsistency.rule')}<select className="h-9 rounded-md border border-input bg-background px-2" value={ruleKey} onChange={(event) => chooseRule(event.target.value)}>{summary.rules.map((rule) => <option key={rule.rule_key} value={rule.rule_key}>{ruleLabel(rule.rule_key)}</option>)}</select></label>}
    {loadError && <Alert tone="danger">{t('dataConsistency.loadError')} <Button variant="ghost" onClick={refresh}>{t('common.retry')}</Button></Alert>}
    {actionError && !selected && !dateIssue && !genericIssue && <Alert tone="danger">{actionError}</Alert>}
    {bulkReport && <Alert tone={bulkReport.action === 'correct' ? (bulkReport.data.failed || bulkReport.data.ignored ? 'warning' : 'success') : (bulkReport.data.failed || bulkReport.data.skipped ? 'warning' : 'success')}>{t(bulkReport.action === 'correct' ? 'dataConsistency.correctionReport' : 'dataConsistency.batchReport', bulkReport.data)}</Alert>}
    {!loadError && !result && summary && <LoadingState message={t('common.loading')} />}
    {result && <section aria-label={t('dataConsistency.title')} className="grid gap-3" id="consistency-detail">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h2 className="text-lg font-semibold">{ruleLabel(ruleKey)}</h2><p role="status">{t('dataConsistency.issuesCount', { count: result.count })}</p></div>
        {canSelect && (result.count > 0 || selectionMode) && <Button variant="secondary" aria-pressed={selectionMode} onClick={() => { if (selectionMode) clearSelection(); setSelectionMode(!selectionMode) }}>{t(selectionMode ? 'dataConsistency.finishSelection' : 'dataConsistency.startSelection')}</Button>}
      </div>
      {selectionMode && canSelect && <div className="grid gap-3 rounded-lg border border-border bg-muted/30 p-3">
        <p role="status">{t('dataConsistency.selectedCount', { count: selectableCount })}</p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={selectVisible}>{t('dataConsistency.selectVisible', { count: result.results.length })}</Button>
          <Button size="sm" variant="secondary" onClick={() => { setAllMatching(true); setSelectedIssues(new Map()); setExcludedIds(new Set()) }}>{t('dataConsistency.selectAllResults', { count: result.count })}</Button>
          <Button size="sm" variant="ghost" onClick={clearSelection}>{t('dataConsistency.clearSelection')}</Button>
        </div>
        <p className="text-sm text-muted-foreground">{t('dataConsistency.batchActionHint')}</p>
        {summary?.capabilities.can_accept && <label className="grid gap-1 text-sm">{t('dataConsistency.reason')}<Textarea value={bulkReason} maxLength={1000} onChange={(event) => setBulkReason(event.target.value)} /></label>}
        <div className="flex flex-wrap gap-2">{canCorrect && <Button disabled={selectableCount === 0 || bulkPending} onClick={(event) => { returnFocus.current = event.currentTarget; setBulkAction('correct'); setBulkConfirm(true) }}>{t(correctionLabel, { count: selectableCount, action: genericActionLabel(ruleKey) })}</Button>}{summary?.capabilities.can_accept && <Button disabled={selectableCount === 0 || bulkPending} onClick={(event) => { returnFocus.current = event.currentTarget; setBulkAction('accept'); setBulkConfirm(true) }}>{t('dataConsistency.acceptSelected', { count: selectableCount })}</Button>}</div>
        {bulkError && !bulkConfirm && <Alert tone="danger">{bulkError}</Alert>}
      </div>}
      {result.results.length === 0 ? <p>{t('dataConsistency.empty')}</p> : <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm"><thead><tr className="border-b border-border bg-muted/40">
          {selectionMode && canSelect && <th scope="col" className="p-3">{t('dataConsistency.selectColumn')}</th>}
          <th scope="col" className="p-3">{t('dataConsistency.issue')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.employee')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.project')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.object')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.status')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.actions')}</th>
        </tr></thead><tbody>{result.results.map((issue) => <tr key={`${issue.rule_key}-${issueId(issue)}`} className="border-b border-border last:border-0">
          {selectionMode && canSelect && <td className="p-3"><CheckboxRow aria-label={t('dataConsistency.selectIssue', { name: issue.label })} checked={allMatching ? !excludedIds.has(issueId(issue)) : selectedIssues.has(issueId(issue))} onChange={() => toggleIssue(issue)}><span className="sr-only">{issue.label}</span></CheckboxRow></td>}
          <td className="p-3"><span>{issue.label}</span>{issue.reason && <div className="mt-1 text-xs text-muted-foreground">{t(issue.reason === 'both' ? 'dataConsistency.boundaryBoth' : issue.reason === 'starts_before_project' ? 'dataConsistency.boundaryStart' : 'dataConsistency.boundaryEnd')} · {dateLabel(issue.child_start_date ?? null)} → {dateLabel(issue.child_end_date ?? null)}</div>}{issue.exception && <div className="mt-1 text-xs text-muted-foreground">{t('dataConsistency.acceptedBy', { user: issue.exception.accepted_by || '—', date: date(issue.exception.accepted_at) })}{issue.exception.reason && <p>{issue.exception.reason}</p>}</div>}</td>
          <td className="p-3">{issue.employee_id ? <Link className="underline" to={`/employees/${issue.employee_id}`}>{issue.employee_name}</Link> : '—'}</td>
          <td className="p-3">{issue.project_id ? <Link className="underline" to={`/projects/${issue.project_id}`}>{issue.project_name}</Link> : issue.team_id ? <Link className="underline" to={`/teams/${issue.team_id}`}>{issue.team_name}</Link> : '—'}</td>
          <td className="p-3">{objectLabel(issue)}</td>
          <td className="p-3">{t(status === 'active' ? 'dataConsistency.active' : 'dataConsistency.accepted')}</td>
          <td className="p-3"><div className="flex flex-wrap gap-2">{status === 'active' && issue.rule_key === PARTICIPANT_RULE && issue.employee_id && issue.project_id && issue.can_add_participant && <Button size="sm" variant="secondary" disabled={pending} onClick={() => void openParticipant(issue)}>{t('dataConsistency.addParticipant')}</Button>}{status === 'active' && issue.reason && dateParent(issue)?.canChange && <Button size="sm" variant="secondary" onClick={(event) => { returnFocus.current = event.currentTarget; setDateIssue(issue); setActionError(null) }}>{actionLabel(issue)}</Button>}{status === 'active' && issue.correction_action === 'apply_correction' && <Button size="sm" variant="secondary" onClick={(event) => { returnFocus.current = event.currentTarget; setGenericIssue(issue); setActionError(null) }}>{genericActionLabel(issue.rule_key)}</Button>}{status === 'active' && issue.manual_url && <Link className="underline" to={issue.manual_url}>{t('dataConsistency.editEmployee')}</Link>}{status === 'active' && issue.rule_key === PROJECT_LEADER_RULE && issue.project_id && <Link className="underline" to={`/projects/${issue.project_id}#project-participants-heading`}>{issue.can_add_participant ? t('dataConsistency.editParticipants') : t('dataConsistency.openProject')}</Link>}{status === 'active' && summary?.capabilities.can_accept && <Button size="sm" variant="secondary" disabled={pending} onClick={(event) => { returnFocus.current = event.currentTarget; setSelected(issue); setReason(''); setActionError(null) }}>{t('dataConsistency.acceptAction')}</Button>}{status === 'accepted' && summary?.capabilities.can_reopen && <Button size="sm" variant="secondary" disabled={pending} onClick={() => void reopen(issue)}>{t('dataConsistency.reopenAction')}</Button>}</div></td>
        </tr>)}</tbody></table>
      </div>}
      <nav className="flex items-center justify-end gap-2" aria-label={t('dataConsistency.pagination')}>
        <Button variant="ghost" disabled={!result.previous} onClick={() => { const next = Math.max(0, offset - LIMIT); setResult(null); setOffset(next); remember({ offset: next }) }}>{t('common.previous')}</Button>
        <span>{t('common.pageOf', { page: Math.floor(offset / LIMIT) + 1, pages: Math.max(1, Math.ceil(result.count / LIMIT)) })}</span>
        <Button variant="ghost" disabled={!result.next} onClick={() => { const next = offset + LIMIT; setResult(null); setOffset(next); remember({ offset: next }) }}>{t('common.next')}</Button>
      </nav>
    </section>}
    {bulkConfirm && <ConfirmDialog title={t(bulkAction === 'correct' ? (participantBatch ? 'dataConsistency.participantConfirmTitle' : lifecycleBatch ? 'dataConsistency.lifecycleConfirmTitle' : 'dataConsistency.correctionConfirmTitle') : 'dataConsistency.batchConfirmTitle')} description={t(bulkAction === 'correct' ? (participantBatch ? 'dataConsistency.participantConfirmDescription' : lifecycleBatch ? 'dataConsistency.lifecycleConfirmDescription' : 'dataConsistency.correctionConfirmDescription') : 'dataConsistency.batchConfirmDescription', { rule: ruleLabel(ruleKey), count: selectableCount, action: genericActionLabel(ruleKey) })} pending={bulkPending} error={bulkError && <Alert tone="danger">{bulkError}</Alert>} onConfirm={() => void runBatch()} onCancel={() => { setBulkConfirm(false); setBulkError(null) }} returnFocus={returnFocus} confirmLabel={t(bulkAction === 'correct' ? correctionLabel : 'dataConsistency.acceptSelected', { count: selectableCount, action: genericActionLabel(ruleKey) })} />}
    {participantIssue && participantIssue.project_id && participantProject && <ParticipantSheet key={participantIssue.contract_id} projectId={String(participantIssue.project_id)} project={participantProject} item={null} initialEmployeeId={participantIssue.employee_id} onClose={() => { setParticipantIssue(null); setParticipantProject(null) }} onSaved={() => { setParticipantIssue(null); setParticipantProject(null); refresh() }} />}
    {dateIssue && previewParent && previewDates && <ConfirmDialog title={actionLabel(dateIssue)} description={t(previewParent.kind === 'employee' ? 'dataConsistency.extendEmployeeDescription' : previewParent.kind === 'fund' ? 'dataConsistency.extendFundDescription' : 'dataConsistency.extendDescription', { startBefore: dateLabel(previewParent.start), startAfter: dateLabel(previewDates.start_date), endBefore: dateLabel(previewParent.end), endAfter: dateLabel(previewDates.end_date) })} pending={pending} error={actionError && <Alert tone="danger">{actionError}</Alert>} onConfirm={() => void extendParent()} onCancel={() => setDateIssue(null)} returnFocus={returnFocus} confirmLabel={t(previewParent.kind === 'employee' ? 'dataConsistency.confirmExtendEmployee' : previewParent.kind === 'fund' ? 'dataConsistency.confirmExtendFund' : 'dataConsistency.confirmExtend')} />}
    {genericIssue && <ConfirmDialog title={genericActionLabel(genericIssue.rule_key)} description={t('dataConsistency.lifecycleUnitConfirm', { issue: genericIssue.label })} pending={pending} error={actionError && <Alert tone="danger">{actionError}</Alert>} onConfirm={() => void applyGenericCorrection()} onCancel={() => setGenericIssue(null)} returnFocus={returnFocus} confirmLabel={genericActionLabel(genericIssue.rule_key)} />}
    {selected && <Sheet open onOpenChange={(open) => { if (!open && !pending) setSelected(null) }}><SheetContent finalFocus={returnFocus}>
      <SheetHeader><SheetTitle>{t('dataConsistency.acceptAction')}</SheetTitle><SheetDescription>{selected.label}</SheetDescription></SheetHeader>
      <form className="grid gap-4" onSubmit={(event) => { event.preventDefault(); void accept() }}>
        <label className="grid gap-1">{t('dataConsistency.reason')}<Textarea value={reason} maxLength={1000} disabled={pending} onChange={(event) => setReason(event.target.value)} /></label>
        {actionError && <Alert tone="danger">{actionError}</Alert>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={pending} onClick={() => setSelected(null)}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{t('dataConsistency.acceptAction')}</Button></div>
      </form>
    </SheetContent></Sheet>}
  </>
}
