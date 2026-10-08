import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { acceptConsistencyIssue, DATA_CONSISTENCY_CHANGED, getConsistencyIssues, getConsistencySummary, reopenConsistencyIssue, type ConsistencyIssue, type ConsistencyIssues, type ConsistencySummary } from '../api/dataConsistency'
import { normalizeMutationError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Textarea } from '../components/ui/textarea'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'

type Status = 'active' | 'accepted'
const LIMIT = 25

export function DataConsistencyPage() {
  const { t, language } = useTranslation()
  const [status, setStatus] = useState<Status>('active')
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [summary, setSummary] = useState<ConsistencySummary | null>(null)
  const [result, setResult] = useState<ConsistencyIssues | null>(null)
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
    getConsistencyIssues(status, offset, LIMIT, controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setResult(data); setLoadError(false) } },
      () => { if (!controller.signal.aborted) setLoadError(true) },
    )
    return () => controller.abort()
  }, [status, offset, revision])

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

  const chooseStatus = (next: Status) => { setStatus(next); setOffset(0); setActionError(null) }
  const date = (value: string) => new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

  return <>
    <PageHeader title={t('dataConsistency.title')} />
    <div className="flex flex-wrap gap-2" role="group" aria-label={t('dataConsistency.status')}>
      <Button variant={status === 'active' ? 'default' : 'secondary'} aria-pressed={status === 'active'} onClick={() => chooseStatus('active')}>{t('dataConsistency.active')} {summary && `(${summary.total})`}</Button>
      <Button variant={status === 'accepted' ? 'default' : 'secondary'} aria-pressed={status === 'accepted'} onClick={() => chooseStatus('accepted')}>{t('dataConsistency.accepted')} {summary && `(${summary.accepted_total})`}</Button>
    </div>
    {loadError && <Alert tone="danger">{t('dataConsistency.loadError')} <Button variant="ghost" onClick={refresh}>{t('common.retry')}</Button></Alert>}
    {actionError && !selected && <Alert tone="danger">{actionError}</Alert>}
    {!loadError && !result && <LoadingState message={t('common.loading')} />}
    {result && <section aria-label={t('dataConsistency.title')} className="grid gap-3">
      <p role="status">{t('dataConsistency.issuesCount', { count: result.count })}</p>
      {result.results.length === 0 ? <p>{t('dataConsistency.empty')}</p> : <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm"><thead><tr className="border-b border-border bg-muted/40">
          <th scope="col" className="p-3">{t('dataConsistency.issue')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.employee')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.project')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.contract')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.status')}</th>
          <th scope="col" className="p-3">{t('dataConsistency.actions')}</th>
        </tr></thead><tbody>{result.results.map((issue) => <tr key={`${issue.rule_key}-${issue.contract_id}`} className="border-b border-border last:border-0">
          <td className="p-3"><span>{issue.label}</span>{issue.exception && <div className="mt-1 text-xs text-muted-foreground">{t('dataConsistency.acceptedBy', { user: issue.exception.accepted_by || '—', date: date(issue.exception.accepted_at) })}{issue.exception.reason && <p>{issue.exception.reason}</p>}</div>}</td>
          <td className="p-3"><Link className="underline" to={`/employees/${issue.employee_id}`}>{issue.employee_name}</Link></td>
          <td className="p-3"><Link className="underline" to={`/projects/${issue.project_id}`}>{issue.project_name}</Link></td>
          <td className="p-3">#{issue.contract_id}</td>
          <td className="p-3">{t(status === 'active' ? 'dataConsistency.active' : 'dataConsistency.accepted')}</td>
          <td className="p-3">{status === 'active' && summary?.capabilities.can_accept && <Button size="sm" variant="secondary" disabled={pending} onClick={(event) => { returnFocus.current = event.currentTarget; setSelected(issue); setReason(''); setActionError(null) }}>{t('dataConsistency.acceptAction')}</Button>}{status === 'accepted' && summary?.capabilities.can_reopen && <Button size="sm" variant="secondary" disabled={pending} onClick={() => void reopen(issue)}>{t('dataConsistency.reopenAction')}</Button>}</td>
        </tr>)}</tbody></table>
      </div>}
      <nav className="flex items-center justify-end gap-2" aria-label={t('dataConsistency.pagination')}>
        <Button variant="ghost" disabled={!result.previous} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>{t('common.previous')}</Button>
        <span>{t('common.pageOf', { page: Math.floor(offset / LIMIT) + 1, pages: Math.max(1, Math.ceil(result.count / LIMIT)) })}</span>
        <Button variant="ghost" disabled={!result.next} onClick={() => setOffset(offset + LIMIT)}>{t('common.next')}</Button>
      </nav>
    </section>}
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
