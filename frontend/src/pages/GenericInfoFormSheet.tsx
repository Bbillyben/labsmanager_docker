import { useEffect, useId, useState, type FormEvent, type RefObject } from 'react'
import { X } from 'lucide-react'
import { createEmployeeGenericInfo, getGenericInfoTypes, updateEmployeeGenericInfo, type EmployeeGenericInfo, type GenericInfoType } from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Input } from '../components/ui/input'
import { NativeSelect } from '../components/ui/native-select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import styles from './EmployeeGenericInfo.module.css'

export function GenericInfoFormSheet({ employeeId, item, onClose, onSaved, returnFocus }: {
  employeeId: string; item: EmployeeGenericInfo | null; onClose: () => void
  onSaved: (item: EmployeeGenericInfo) => void; returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const id = useId()
  const [value, setValue] = useState(item?.value ?? '')
  const [typeId, setTypeId] = useState('')
  const [types, setTypes] = useState<GenericInfoType[] | null>(null)
  const [catalogueError, setCatalogueError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  useEffect(() => {
    if (item) return
    const controller = new AbortController()
    getGenericInfoTypes(controller.signal).then(
      (data) => { if (!controller.signal.aborted) { setTypes(data); setCatalogueError(false) } },
      () => { if (!controller.signal.aborted) setCatalogueError(true) },
    )
    return () => controller.abort()
  }, [item, attempt])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => item
      ? updateEmployeeGenericInfo(employeeId, item.id, value)
      : createEmployeeGenericInfo(employeeId, { type_id: Number(typeId), value }))
    if (result) onSaved(result.data)
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}>
    <SheetContent finalFocus={returnFocus}>
      <Button className={styles.close} size="icon-sm" variant="ghost" aria-label={t('common.close')} disabled={mutation.pending} onClick={onClose}><X aria-hidden="true" /></Button>
      <SheetHeader><SheetTitle>{t(item ? 'genericInfo.edit' : 'genericInfo.add')}</SheetTitle><SheetDescription>{t('genericInfo.formDescription')}</SheetDescription></SheetHeader>
      <form className={styles.form} onSubmit={(event) => void submit(event)} aria-busy={mutation.pending}>
        {error && <Alert tone="danger">{error.messages.length ? error.messages.join(' ') : t(`genericInfo.error.${error.kind}`)}{Object.entries(error.fields).filter(([key]) => !['type_id', 'value'].includes(key)).map(([key, messages]) => <p key={key}>{messages.join(' ')}</p>)}</Alert>}
        {item ? <p><strong>{t('genericInfo.type')}: </strong>{item.type.name}</p> : <>
          <label htmlFor={`${id}-type`}>{t('genericInfo.type')}</label>
          {catalogueError ? <Alert tone="danger">{t('genericInfo.catalogueError')} <Button onClick={() => setAttempt((a) => a + 1)} variant="ghost">{t('common.retry')}</Button></Alert> : !types ? <p role="status">{t('genericInfo.loading')}</p> : <>
            <NativeSelect id={`${id}-type`} required value={typeId} onChange={(event) => setTypeId(event.target.value)} disabled={mutation.pending} aria-invalid={!!error?.fields.type_id?.length} aria-describedby={error?.fields.type_id?.length ? `${id}-type-error` : undefined}>
              <option value="">{t('genericInfo.chooseType')}</option>
              {types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}
            </NativeSelect>
            {!types.length && <p>{t('genericInfo.noTypes')}</p>}
          </>}
          {error?.fields.type_id && <p id={`${id}-type-error`} className={styles.fieldError}>{error.fields.type_id.join(' ')}</p>}
        </>}
        <label htmlFor={`${id}-value`}>{t('genericInfo.value')}</label>
        <Input id={`${id}-value`} value={value} maxLength={150} disabled={mutation.pending} onChange={(event) => setValue(event.target.value)} aria-invalid={!!error?.fields.value?.length} aria-describedby={error?.fields.value?.length ? `${id}-value-error` : undefined} />
        {error?.fields.value && <p id={`${id}-value-error`} className={styles.fieldError}>{error.fields.value.join(' ')}</p>}
        <div className={styles.buttons}><Button disabled={mutation.pending} onClick={onClose}>{t('genericInfo.cancel')}</Button><Button type="submit" variant="primary" disabled={mutation.pending || (!item && (!types?.length || !typeId))}>{t(mutation.pending ? 'genericInfo.pending' : 'genericInfo.save')}</Button></div>
      </form>
    </SheetContent>
  </Sheet>
}
