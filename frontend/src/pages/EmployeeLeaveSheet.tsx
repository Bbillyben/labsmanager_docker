import { Pencil, Trash2, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { createEmployeeLeave, deleteEmployeeLeave, getLeaveTypes, updateEmployeeLeave, type EmployeeLeave, type LeaveCapabilities, type LeaveTypeOption, type LeaveWrite } from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { halfDayLabel } from '../calendar/halfDayPresentation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import styles from './EmployeeLeaveSheet.module.css'

export function EmployeeLeaveSheet({ employeeId, leave, initialDates, capabilities, onClose, onSaved, onDeleted, createLeave = createEmployeeLeave, updateLeave = updateEmployeeLeave, deleteLeave = deleteEmployeeLeave, employeeOptions, onEmployeeChange }: {
  employeeId: string
  leave: EmployeeLeave | null
  initialDates?: { start_date: string; end_date: string }
  capabilities: LeaveCapabilities
  onClose: () => void
  onSaved: (leave: EmployeeLeave) => void
  onDeleted: () => void
  createLeave?: (employeeId: string, value: LeaveWrite) => Promise<EmployeeLeave>
  updateLeave?: (employeeId: string, leaveId: number, value: LeaveWrite) => Promise<EmployeeLeave>
  deleteLeave?: (employeeId: string, leaveId: number) => Promise<void>
  employeeOptions?: Array<{ id: number; title: string }>
  onEmployeeChange?: (employeeId: string) => void
}) {
  const { language, t } = useTranslation()
  const id = useId()
  const [mode, setMode] = useState<'view' | 'create' | 'edit'>(leave ? 'view' : 'create')
  const [current, setCurrent] = useState(leave)
  const [draft, setDraft] = useState<LeaveWrite>(() => ({
    type_id: leave?.type.id ?? 0,
    start_date: leave?.start_date ?? initialDates?.start_date ?? '',
    start_period: leave?.start_period ?? 'ST',
    end_date: leave?.end_date ?? initialDates?.end_date ?? '',
    end_period: leave?.end_period ?? 'EN',
    comment: leave?.comment ?? '',
  }))
  const [types, setTypes] = useState<LeaveTypeOption[] | null>(null)
  const [catalogueError, setCatalogueError] = useState(false)
  const [catalogueAttempt, setCatalogueAttempt] = useState(0)
  const [confirming, setConfirming] = useState(false)
  const deleteButton = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const deletion = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const deleteError = deletion.error ? normalizeMutationError(deletion.error) : null

  useEffect(() => {
    if (mode === 'view') return
    const controller = new AbortController()
    getLeaveTypes(controller.signal).then((result) => {
      if (!controller.signal.aborted) { setTypes(result); setCatalogueError(false) }
    }, () => { if (!controller.signal.aborted) setCatalogueError(true) })
    return () => controller.abort()
  }, [mode, catalogueAttempt])

  const change = <K extends keyof LeaveWrite>(key: K, value: LeaveWrite[K]) => setDraft((previous) => ({ ...previous, [key]: value }))
  async function save(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => mode === 'create'
      ? createLeave(employeeId, draft)
      : updateLeave(employeeId, current!.id, draft))
    if (result) { setCurrent(result.data); setMode('view'); onSaved(result.data) }
  }
  async function remove() {
    if (!current) return
    const result = await deletion.run(() => deleteLeave(employeeId, current.id))
    if (result) { setConfirming(false); onDeleted() }
  }
  const resetDraft = () => {
    if (current) setDraft({ type_id: current.type.id, start_date: current.start_date, start_period: current.start_period, end_date: current.end_date, end_period: current.end_period, comment: current.comment ?? '' })
    setMode('view')
  }
  const formError = error && (error.messages.join(' ') || Object.values(error.fields).flat().join(' ') || t(`genericInfo.error.${error.kind}`))

  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending && !deletion.pending) onClose() }}>
    <SheetContent>
      <Button aria-label={t('common.close')} className={styles.close} disabled={mutation.pending || deletion.pending} onClick={onClose} size="icon-sm" variant="ghost"><X aria-hidden="true" /></Button>
      <SheetHeader><SheetTitle>{t(mode === 'create' ? 'leaves.add' : mode === 'edit' ? 'leaves.edit' : 'leaves.details')}</SheetTitle><SheetDescription>{current?.type.name ?? t('leaves.formDescription')}</SheetDescription></SheetHeader>
      {mode === 'view' && current && <>
        <dl className={styles.details}>
          <div><dt>{t('leaves.type')}</dt><dd>{current.type.name}</dd></div>
          <div><dt>{t('leaves.start')}</dt><dd>{formatDate(current.start_date, language)} · {t(current.start_period === 'ST' ? 'leaves.startOfDay' : 'leaves.midday')}</dd></div>
          <div><dt>{t('leaves.end')}</dt><dd>{formatDate(current.end_date, language)} · {t(current.end_period === 'MI' ? 'leaves.midday' : 'leaves.endOfDay')}</dd></div>
          <div><dt>{t('leaves.duration')}</dt><dd>{t('leaves.days', { count: current.day_count })}{halfDayLabel(current, t) ? ` · ${halfDayLabel(current, t)}` : ''}</dd></div>
          <div><dt>{t('leaves.comment')}</dt><dd>{current.comment || '—'}</dd></div>
        </dl>
        <div className={styles.actions}>
          {capabilities.can_change && <Button onClick={() => setMode('edit')} size="sm" variant="secondary"><Pencil aria-hidden="true" />{t('leaves.edit')}</Button>}
          {capabilities.can_delete && <Button onClick={(event) => { deleteButton.current = event.currentTarget; setConfirming(true) }} size="sm" variant="destructive"><Trash2 aria-hidden="true" />{t('genericInfo.delete')}</Button>}
        </div>
      </>}
      {mode !== 'view' && <form aria-busy={mutation.pending} className={styles.form} onSubmit={(event) => void save(event)}>
        {formError && <Alert tone="danger">{formError}</Alert>}
        {mode === 'create' && employeeOptions && <><label htmlFor={`${id}-employee`}>{t('projectCalendar.employee')}</label><select id={`${id}-employee`} onChange={(event) => onEmployeeChange?.(event.target.value)} value={employeeId}>{employeeOptions.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></>}
        <label htmlFor={`${id}-type`}>{t('leaves.type')}</label>
        {catalogueError ? <Alert tone="danger">{t('leaves.typeError')} <Button onClick={() => setCatalogueAttempt((n) => n + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></Alert> : !types ? <p role="status">{t('genericInfo.loading')}</p> : <select id={`${id}-type`} required value={draft.type_id || ''} onChange={(event) => change('type_id', Number(event.target.value))}>
          <option value="">{t('leaves.chooseType')}</option>
          {types.map((type) => <option key={type.id} value={type.id}>{'　'.repeat(type.depth)}{type.name}</option>)}
        </select>}
        <label htmlFor={`${id}-start`}>{t('leaves.start')}</label>
        <input id={`${id}-start`} required type="date" value={draft.start_date} onChange={(event) => change('start_date', event.target.value)} />
        <label htmlFor={`${id}-start-period`}>{t('leaves.startPeriod')}</label>
        <select id={`${id}-start-period`} value={draft.start_period} onChange={(event) => change('start_period', event.target.value as LeaveWrite['start_period'])}>
          <option value="ST">{t('leaves.startOfDay')}</option><option value="MI">{t('leaves.midday')}</option>
        </select>
        <label htmlFor={`${id}-end`}>{t('leaves.end')}</label>
        <input id={`${id}-end`} required type="date" value={draft.end_date} onChange={(event) => change('end_date', event.target.value)} />
        <label htmlFor={`${id}-end-period`}>{t('leaves.endPeriod')}</label>
        <select id={`${id}-end-period`} value={draft.end_period} onChange={(event) => change('end_period', event.target.value as LeaveWrite['end_period'])}>
          <option value="MI">{t('leaves.midday')}</option><option value="EN">{t('leaves.endOfDay')}</option>
        </select>
        <label htmlFor={`${id}-comment`}>{t('leaves.comment')}</label>
        <textarea id={`${id}-comment`} value={draft.comment} onChange={(event) => change('comment', event.target.value)} />
        <div className={styles.actions}>
          <Button disabled={mutation.pending || !types?.length || !draft.type_id} type="submit">{t('genericInfo.save')}</Button>
          <Button disabled={mutation.pending} onClick={mode === 'create' ? onClose : resetDraft} type="button" variant="ghost">{t('genericInfo.cancel')}</Button>
        </div>
      </form>}
      {confirming && current && <ConfirmDialog title={t('leaves.deleteTitle')} description={t('leaves.deleteDescription', { name: current.type.name })} pending={deletion.pending} onCancel={() => setConfirming(false)} onConfirm={() => void remove()} returnFocus={deleteButton} error={deleteError && <Alert tone="danger">{deleteError.messages.join(' ') || t(`genericInfo.error.${deleteError.kind}`)}</Alert>} />}
    </SheetContent>
  </Sheet>
}

function formatDate(value: string, language: string) {
  return new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}
