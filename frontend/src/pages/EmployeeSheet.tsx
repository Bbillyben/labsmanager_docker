import { useState, type FormEvent, type RefObject } from 'react'
import { X } from 'lucide-react'
import { updateEmployee, type EmployeeDetail, type EmployeeDetailWrite } from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function EmployeeSheet({ employee, onClose, onSaved, returnFocus }: {
  employee: EmployeeDetail
  onClose: () => void
  onSaved: () => void
  returnFocus?: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<EmployeeDetailWrite>({
    birth_date: employee.birth_date,
    entry_date: employee.entry_date,
    exit_date: employee.exit_date,
    email: employee.email,
    is_active: employee.is_active,
  })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const message = error && (error.messages.join(' ') || Object.values(error.fields).flat().join(' ') || t('employee.saveError'))
  const change = <K extends keyof EmployeeDetailWrite>(key: K, value: EmployeeDetailWrite[K]) => setDraft((current) => ({ ...current, [key]: value }))

  async function save(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => updateEmployee(employee.id, draft))
    if (result) onSaved()
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}>
    <SheetContent finalFocus={returnFocus}>
      <Button aria-label={t('common.close')} className="absolute right-4 top-4" disabled={mutation.pending} onClick={onClose} size="icon-sm" variant="ghost"><X /></Button>
      <SheetHeader><SheetTitle>{t('employee.edit')}</SheetTitle><SheetDescription>{employee.first_name} {employee.last_name}</SheetDescription></SheetHeader>
      <form className="grid gap-3" aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
        {message && <Alert tone="danger">{message}</Alert>}
        <label className="grid gap-1">{t('employee.birthDate')}<InputField type="date" value={draft.birth_date ?? ''} onChange={(value) => change('birth_date', value || null)} /></label>
        <label className="grid gap-1">{t('employee.entryDate')}<InputField type="date" value={draft.entry_date ?? ''} onChange={(value) => change('entry_date', value || null)} /></label>
        <label className="grid gap-1">{t('employee.exitDate')}<InputField type="date" value={draft.exit_date ?? ''} onChange={(value) => change('exit_date', value || null)} /></label>
        <label className="grid gap-1">{t('employee.email')}<InputField type="email" value={draft.email ?? ''} onChange={(value) => change('email', value || null)} /></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={draft.is_active} onChange={(event) => change('is_active', event.target.checked)} />{t('common.active')}</label>
        <div className="flex justify-end gap-2"><Button disabled={mutation.pending} onClick={onClose} type="button" variant="ghost">{t('common.cancel')}</Button><Button disabled={mutation.pending} type="submit">{t(mutation.pending ? 'common.saving' : 'common.save')}</Button></div>
      </form>
    </SheetContent>
  </Sheet>
}

function InputField({ onChange, ...props }: Omit<React.ComponentProps<'input'>, 'onChange'> & { onChange: (value: string) => void }) {
  return <input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" onChange={(event) => onChange(event.target.value)} {...props} />
}
