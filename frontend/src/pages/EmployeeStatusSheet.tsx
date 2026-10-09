import { useState, type FormEvent, type RefObject } from 'react'
import { addEmployeeStatus, updateEmployeeStatus, type EmployeeStatusHistoryItem, type EmployeeStatusOptions, type EmployeeStatusWrite } from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function EmployeeStatusSheet({ employeeId, status, options, defaultDates, onClose, onSaved, returnFocus }: {
  employeeId: string
  status: EmployeeStatusHistoryItem | null
  options: EmployeeStatusOptions
  defaultDates: Pick<EmployeeStatusWrite, 'start_date' | 'end_date'>
  onClose: () => void
  onSaved: () => void
  returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<EmployeeStatusWrite>({
    type: status?.type.id,
    start_date: status ? status.start_date : defaultDates.start_date,
    end_date: status ? status.end_date : defaultDates.end_date,
    is_contractual: status?.contractuality.code ?? 'c',
  })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const errorText = (value: string) => value === 'end_before_start' ? t('employee.statusDateError') : value
  const fieldError = (field: string) => error?.fields[field]?.map(errorText).join(' ')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!status && !draft.type) return
    const result = await mutation.run(() => status
      ? updateEmployeeStatus(employeeId, status.id, { start_date: draft.start_date, end_date: draft.end_date, is_contractual: draft.is_contractual })
      : addEmployeeStatus(employeeId, draft))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(status ? 'employee.editStatus' : 'employee.addStatus')}</SheetTitle><SheetDescription>{t('employee.statusDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" aria-busy={mutation.pending} onSubmit={(event) => void submit(event)}>
      {error && (error.messages.length > 0 || Object.keys(error.fields).some((field) => !['type', 'start_date', 'end_date', 'is_contractual'].includes(field))) &&
        <Alert tone="danger">{[...error.messages, ...Object.entries(error.fields).filter(([field]) => !['type', 'start_date', 'end_date', 'is_contractual'].includes(field)).flatMap(([, messages]) => messages)].map(errorText).join(' ') || t('employee.statusSaveError')}</Alert>}
      <label className="grid gap-1">{t('employee.statusType')}<select className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={draft.type ?? ''} disabled={Boolean(status)} onChange={(event) => setDraft((value) => ({ ...value, type: Number(event.target.value) || undefined }))}>
        <option value="">{t('employee.selectStatus')}</option>{options.types.map((item) => <option value={item.id} key={item.id}>{item.name} ({item.shortname})</option>)}
      </select>{fieldError('type') && <span role="alert" className="text-sm text-destructive">{fieldError('type')}</span>}</label>
      <label className="grid gap-1">{t('employee.contractuality')}<select className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" value={draft.is_contractual} onChange={(event) => setDraft((value) => ({ ...value, is_contractual: event.target.value }))}>{options.contractuality.map((item) => <option value={item.code} key={item.code}>{item.label}</option>)}</select>{fieldError('is_contractual') && <span role="alert" className="text-sm text-destructive">{fieldError('is_contractual')}</span>}</label>
      <label className="grid gap-1">{t('team.startDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={draft.start_date ?? ''} onChange={(event) => setDraft((value) => ({ ...value, start_date: event.target.value || null }))} />{fieldError('start_date') && <span role="alert" className="text-sm text-destructive">{fieldError('start_date')}</span>}</label>
      <label className="grid gap-1">{t('team.endDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={draft.end_date ?? ''} onChange={(event) => setDraft((value) => ({ ...value, end_date: event.target.value || null }))} />{fieldError('end_date') && <span role="alert" className="text-sm text-destructive">{fieldError('end_date')}</span>}</label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!status && !draft.type)}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
