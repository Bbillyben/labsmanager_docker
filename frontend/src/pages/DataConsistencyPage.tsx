import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { acceptConsistencyIssue, DATA_CONSISTENCY_CHANGED, getConsistencyIssues, getConsistencySummary, reopenConsistencyIssue, type ConsistencyIssue, type ConsistencyIssues, type ConsistencySummary } from '../api/dataConsistency'
import { normalizeMutationError } from '../api/errors'
import { getEmployee, updateEmployee, type EmployeeDetail } from '../api/employees'
import { getFundDetail, updateFund, type Fund } from '../api/funding'
import { getProject, updateProject, type ProjectOverview } from '../api/projects'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { LoadingState } from '../components/LoadingState'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Textarea } from '../components/ui/textarea'
import { useTranslation } from '../i18n/i18n'
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

export function DataConsistencyPage() {
  const { t, language } = useTranslation()
  const [status, setStatus] = useState<Status>('active')
  const [ruleKey, setRuleKey] = useState(PARTICIPANT_RULE)
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [summary, setSummary] = useState<ConsistencySummary | null>(null)
  const [result, setResult] = useState<ConsistencyIssues | null>(null)
  const [projects, setProjects] = useState<Record<number, ProjectOverview>>({})
  const [employees, setEmployees] = useState<Record<number, EmployeeDetail>>({})
  const [funds, setFunds] = useState<Record<number, Fund>>({})
  const [participantIssue, setParticipantIssue] = useState<ConsistencyIssue | null>(null)
  const [dateIssue, setDateIssue] = useState<ConsistencyIssue | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [selected, setSelected] = useState<ConsistencyIssue | null>(null)
  const [reason, setReason] = useState('')
  const [pending, setPending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const returnFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getConsistencySummary(controller.signal).then(
      (data) => { if (!controller.signal.aborted) setSummary(data) },
      () => { if (!controller.signal.aborted) setLoadError(true) },
    )
    return () => controller.abort()
  }, [revision])

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
    const controller = new AbortController()
    setProjects({}); setEmployees({}); setFunds({})
    if (status === 'active' && result) {
      const projectIds = [...new Set(result.results.filter((issue) => parentKind(issue) === 'project').map((issue) => issue.project_id))]
      const employeeIds = [...new Set(result.results.filter((issue) => parentKind(issue) === 'employee').map((issue) => issue.employee_id).filter((id): id is number => id !== undefined))]
      const fundIssues = result.results.filter((issue) => parentKind(issue) === 'fund' && issue.fund_id)
      void Promise.all(projectIds.map(async (id) => {
        try { return [id, await getProject(String(id), controller.signal)] as const }
        catch { return null }
      })).then((entries) => {
        if (!controller.signal.aborted) setProjects(Object.fromEntries(entries.filter((entry): entry is readonly [number, ProjectOverview] => entry !== null)))
      })
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
    setOffset(0)
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
    const project = projects[issue.project_id]
    return project && { kind, id: project.id, start: project.start_date, end: project.end_date, canChange: project.capabilities.can_change }
  }

  const extendParent = async () => {
    if (!dateIssue) return
    const parent = dateParent(dateIssue)
    if (!parent?.canChange) return
    const dates = extendedDates(parent.start, parent.end, dateIssue)
    setPending(true); setActionError(null)
    try {
      if (parent.kind === 'employee') await updateEmployee(parent.id, { entry_date: dates.start_date, exit_date: dates.end_date })
      else if (parent.kind === 'fund') await updateFund(String(dateIssue.project_id), parent.id, dates)
      else await updateProject(parent.id, dates)
      setDateIssue(null)
      refresh()
    } catch (error) { setActionError(normalizeMutationError(error).messages.join(' ') || t('dataConsistency.actionError')) }
    finally { setPending(false) }
  }

  const chooseStatus = (next: Status) => { setStatus(next); setOffset(0); setActionError(null) }
  const chooseRule = (next: string) => { setRuleKey(next); setOffset(0); setActionError(null) }
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
      default: return t('dataConsistency.rule.contract_employee_not_project_participant')
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
    if (issue.expense_id) return `${t('dataConsistency.expense')} #${issue.expense_id}`
    if (issue.milestone_id) return `${t(issue.rule_key === TASK_DATES_RULE ? 'dataConsistency.task' : 'dataConsistency.milestone')} #${issue.milestone_id}`
    if (issue.contract_id) return `${t('dataConsistency.contract')} #${issue.contract_id}`
    if (issue.fund_id) return `${t('dataConsistency.fund')} #${issue.fund_id}`
    return `${t('dataConsistency.project')} #${issue.project_id}`
  }
  const previewParent = dateIssue && dateParent(dateIssue)
  const previewDates = previewParent && dateIssue ? extendedDates(previewParent.start, previewParent.end, dateIssue) : null
  const selectedCount = summary?.rules.find((rule) => rule.rule_key === ruleKey)

  return <>
    <PageHeader title={t('dataConsistency.title')} />
    <div className="flex flex-wrap gap-2" role="group" aria-label={t('dataConsistency.status')}>
      <Button variant={status === 'active' ? 'default' : 'secondary'} aria-pressed={status === 'active'} onClick={() => chooseStatus('active')}>{t('dataConsistency.active')} {summary && `(${selectedCount?.count ?? summary.total})`}</Button>
      <Button variant={status === 'accepted' ? 'default' : 'secondary'} aria-pressed={status === 'accepted'} onClick={() => chooseStatus('accepted')}>{t('dataConsistency.accepted')} {summary && `(${selectedCount?.accepted_count ?? summary.accepted_total})`}</Button>
    </div>
    {summary && summary.rules.length > 1 && <label className="flex items-center gap-2">{t('dataConsistency.rule')}<select className="h-9 rounded-md border border-input bg-background px-2" value={ruleKey} onChange={(event) => chooseRule(event.target.value)}>{summary.rules.map((rule) => <option key={rule.rule_key} value={rule.rule_key}>{ruleLabel(rule.rule_key)}</option>)}</select></label>}
    {loadError && <Alert tone="danger">{t('dataConsistency.loadError')} <Button variant="ghost" onClick={refresh}>{t('common.retry')}</Button></Alert>}
    {actionError && !selected && !dateIssue && <Alert tone="danger">{actionError}</Alert>}
    {!loadError && !result && <LoadingState message={t('common.loading')} />}
    {result && <section aria-label={t('dataConsistency.title')} className="grid gap-3">
      <p role="status">{t('dataConsistency.issuesCount', { count: result.count })}</p>
      {result.results.length === 0 ? <p>{t('dataConsistency.empty')}</p> : <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm"><thead><tr className="border-b border-border bg-muted/40">
          <th scope="col" className="p-3">{t('dataConsistency.issue')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.employee')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.project')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.object')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.status')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.actions')}</th>
        </tr></thead><tbody>{result.results.map((issue) => <tr key={`${issue.rule_key}-${issue.expense_id ?? issue.milestone_id ?? issue.contract_id ?? issue.fund_id ?? issue.project_id}`} className="border-b border-border last:border-0">
          <td className="p-3"><span>{issue.label}</span>{issue.reason && <div className="mt-1 text-xs text-muted-foreground">{t(issue.reason === 'both' ? 'dataConsistency.boundaryBoth' : issue.reason === 'starts_before_project' ? 'dataConsistency.boundaryStart' : 'dataConsistency.boundaryEnd')} · {dateLabel(issue.child_start_date ?? null)} → {dateLabel(issue.child_end_date ?? null)}</div>}{issue.exception && <div className="mt-1 text-xs text-muted-foreground">{t('dataConsistency.acceptedBy', { user: issue.exception.accepted_by || '—', date: date(issue.exception.accepted_at) })}{issue.exception.reason && <p>{issue.exception.reason}</p>}</div>}</td>
          <td className="p-3">{issue.employee_id ? <Link className="underline" to={`/employees/${issue.employee_id}`}>{issue.employee_name}</Link> : '—'}</td>
          <td className="p-3"><Link className="underline" to={`/projects/${issue.project_id}`}>{issue.project_name}</Link></td>
          <td className="p-3">{objectLabel(issue)}</td>
          <td className="p-3">{t(status === 'active' ? 'dataConsistency.active' : 'dataConsistency.accepted')}</td>
          <td className="p-3"><div className="flex flex-wrap gap-2">{status === 'active' && issue.rule_key === PARTICIPANT_RULE && issue.employee_id && projects[issue.project_id]?.participants.capabilities.can_add && <Button size="sm" variant="secondary" onClick={() => setParticipantIssue(issue)}>{t('dataConsistency.addParticipant')}</Button>}{status === 'active' && issue.reason && dateParent(issue)?.canChange && <Button size="sm" variant="secondary" onClick={(event) => { returnFocus.current = event.currentTarget; setDateIssue(issue); setActionError(null) }}>{actionLabel(issue)}</Button>}{status === 'active' && issue.rule_key === PROJECT_LEADER_RULE && <Link className="underline" to={`/projects/${issue.project_id}#project-participants-heading`}>{projects[issue.project_id]?.participants.capabilities.can_add ? t('dataConsistency.editParticipants') : t('dataConsistency.openProject')}</Link>}{status === 'active' && summary?.capabilities.can_accept && <Button size="sm" variant="secondary" disabled={pending} onClick={(event) => { returnFocus.current = event.currentTarget; setSelected(issue); setReason(''); setActionError(null) }}>{t('dataConsistency.acceptAction')}</Button>}{status === 'accepted' && summary?.capabilities.can_reopen && <Button size="sm" variant="secondary" disabled={pending} onClick={() => void reopen(issue)}>{t('dataConsistency.reopenAction')}</Button>}</div></td>
        </tr>)}</tbody></table>
      </div>}
      <nav className="flex items-center justify-end gap-2" aria-label={t('dataConsistency.pagination')}>
        <Button variant="ghost" disabled={!result.previous} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>{t('common.previous')}</Button>
        <span>{t('common.pageOf', { page: Math.floor(offset / LIMIT) + 1, pages: Math.max(1, Math.ceil(result.count / LIMIT)) })}</span>
        <Button variant="ghost" disabled={!result.next} onClick={() => setOffset(offset + LIMIT)}>{t('common.next')}</Button>
      </nav>
    </section>}
    {participantIssue && projects[participantIssue.project_id] && <ParticipantSheet key={participantIssue.contract_id} projectId={String(participantIssue.project_id)} project={projects[participantIssue.project_id]} item={null} initialEmployeeId={participantIssue.employee_id} onClose={() => setParticipantIssue(null)} onSaved={() => { setParticipantIssue(null); refresh() }} />}
    {dateIssue && previewParent && previewDates && <ConfirmDialog title={actionLabel(dateIssue)} description={t(previewParent.kind === 'employee' ? 'dataConsistency.extendEmployeeDescription' : previewParent.kind === 'fund' ? 'dataConsistency.extendFundDescription' : 'dataConsistency.extendDescription', { startBefore: dateLabel(previewParent.start), startAfter: dateLabel(previewDates.start_date), endBefore: dateLabel(previewParent.end), endAfter: dateLabel(previewDates.end_date) })} pending={pending} error={actionError && <Alert tone="danger">{actionError}</Alert>} onConfirm={() => void extendParent()} onCancel={() => setDateIssue(null)} returnFocus={returnFocus} confirmLabel={t(previewParent.kind === 'employee' ? 'dataConsistency.confirmExtendEmployee' : previewParent.kind === 'fund' ? 'dataConsistency.confirmExtendFund' : 'dataConsistency.confirmExtend')} />}
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
