import { useEffect, useMemo, useState, type RefObject } from 'react'
import { ApiError } from '../api/errors'
import { applyProjectPlanningDelay, previewProjectPlanningDelay, type PlanningDelayIntent, type PlanningDelayNode, type PlanningDelayPreview } from '../api/planning'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Input } from '../components/ui/input'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import styles from './ProjectPlanningDelaySheet.module.css'

type Props = { projectId: string; rootIds: number[]; returnFocus: RefObject<HTMLElement | null>; onClose: () => void; onApplied: () => void }

export function ProjectPlanningDelaySheet({ projectId, rootIds, returnFocus, onClose, onApplied }: Props) {
  const { t } = useTranslation()
  const [days, setDays] = useState('14')
  const [cuts, setCuts] = useState<number[]>([])
  const [preview, setPreview] = useState<PlanningDelayPreview | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const validDays = Number.isInteger(Number(days)) && Number(days) > 0
  const intent = useMemo<PlanningDelayIntent>(() => ({ root_ids: rootIds, blocked_dependency_ids: cuts, days: Number(days) }), [rootIds, cuts, days])

  useEffect(() => {
    if (!validDays) { setPreview(null); setPreviewing(false); return }
    const controller = new AbortController()
    setPreview(null)
    setPreviewing(true)
    setError('')
    const timer = window.setTimeout(() => {
      previewProjectPlanningDelay(projectId, intent, controller.signal)
        .then((result) => { if (!controller.signal.aborted) setPreview(result) })
        .catch(() => { if (!controller.signal.aborted) setError(t('planning.delayPreviewError')) })
        .finally(() => { if (!controller.signal.aborted) setPreviewing(false) })
    }, 150)
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [projectId, intent, validDays, reload, t])

  async function apply() {
    if (!preview || applying) return
    setApplying(true)
    setError('')
    try {
      await applyProjectPlanningDelay(projectId, intent, preview.revision)
      onApplied()
    } catch (cause) {
      setError(t(cause instanceof ApiError && cause.status === 409 ? 'planning.delayChanged' : 'planning.delayApplyError'))
      if (cause instanceof ApiError && cause.status === 409) setPreview(null)
    } finally { setApplying(false) }
  }

  const nodes = new Map(preview?.nodes.map((node) => [node.id, node]) ?? [])
  const children = new Map<number, PlanningDelayPreview['edges']>()
  for (const edge of preview?.edges ?? []) children.set(edge.predecessor_id, [...(children.get(edge.predecessor_id) ?? []), edge])
  const shown = new Set<number>()

  function branch(node: PlanningDelayNode, edgeId: number | null, depth: number, pathActive: boolean): React.ReactNode {
    const cut = edgeId !== null && cuts.includes(edgeId)
    const active = pathActive && !cut && node.eligible
    const duplicate = shown.has(node.id)
    shown.add(node.id)
    return <li className={styles.node} key={`${edgeId ?? 'root'}:${node.id}`} style={{ paddingInlineStart: `${depth * 16}px` }}>
      <div className={`${styles.line} ${!active ? styles.excluded : ''}`}>
        {edgeId !== null && <Button type="button" variant="ghost" size="xs" aria-pressed={!cut} aria-label={t(cut ? 'planning.delayResumeBranch' : 'planning.delayStopBranch', { name: node.name })} disabled={applying} onClick={() => setCuts((current) => cut ? current.filter((id) => id !== edgeId) : [...current, edgeId])}>{cut ? '↪' : '⊣'}</Button>}
        <span><strong>{node.name}</strong> <small>· {node.project.name}</small>{duplicate && <small> · {t('planning.delayShared')}</small>}</span>
        {!node.eligible && <small>{t(`planning.delayUnavailable.${node.unavailable_reason ?? 'read_only'}`)}</small>}
        {node.affected && !active && <small>{t('planning.delayOtherPath')}</small>}
      </div>
      {!!children.get(node.id)?.length && <ol className={styles.tree}>{children.get(node.id)!.map((edge) => {
        const child = nodes.get(edge.successor_id)
        return child ? branch(child, edge.id, depth + 1, active) : null
      })}</ol>}
    </li>
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !applying) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t('planning.delayTitle')}</SheetTitle><SheetDescription>{t('planning.delayDescription')}</SheetDescription></SheetHeader>
    <div className={styles.content}>
      <label className={styles.days}>{t('planning.delayBy')} <Input type="number" min="1" step="1" value={days} disabled={applying} onChange={(event) => setDays(event.target.value)} /> {t('planning.delayDays')}</label>
      {!validDays && <Alert tone="warning">{t('planning.delayPositive')}</Alert>}
      <h3>{t('planning.delayPropagation')}</h3>
      <p className={styles.hint}>{t('planning.delayHint')}</p>
      {previewing && <p role="status">{t('common.loading')}</p>}
      {error && <Alert tone="danger">{error} <Button type="button" variant="ghost" onClick={() => setReload((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
      {preview && <>
        <ol className={styles.tree} aria-label={t('planning.delayPropagation')}>{rootIds.map((id) => { const root = nodes.get(id); return root ? branch(root, null, 0, true) : null })}</ol>
        <p className={styles.summary} role="status">{t('planning.delaySummary', { count: preview.affected.length, days: preview.days })} · {t('planning.delayExcluded', { count: preview.excluded_ids.length })}</p>
        <p className={styles.hint}>{t('planning.delayVisibleOnly')}</p>
      </>}
      <div className={styles.actions}><Button type="button" variant="ghost" disabled={applying} onClick={onClose}>{t('common.cancel')}</Button><Button type="button" disabled={!preview || previewing || applying || !preview.affected.length} onClick={() => void apply()}>{t(applying ? 'planning.delayApplying' : 'planning.delayApply')}</Button></div>
    </div>
  </SheetContent></Sheet>
}
