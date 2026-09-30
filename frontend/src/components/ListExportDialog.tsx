import { Dialog } from '@base-ui/react/dialog'
import { useState, type FormEvent, type RefObject } from 'react'
import { exportList, type ListExportEntity, type ListExportFormat } from '../api/listExports'
import { normalizeMutationError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

const formats: ListExportFormat[] = ['xlsx', 'csv', 'tsv', 'xls']

export function ListExportDialog({ entity, listQuery, returnFocus, onClose }: {
  entity: ListExportEntity
  listQuery: string
  returnFocus: RefObject<HTMLElement | null>
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [format, setFormat] = useState<ListExportFormat>('xlsx')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    setPending(true)
    setError(null)
    try {
      const file = await exportList(entity, listQuery, format)
      const url = URL.createObjectURL(file.blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = file.filename ?? `${entity}.${format}`
      anchor.style.display = 'none'
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      onClose()
    } catch (cause) {
      const normalized = normalizeMutationError(cause)
      setError([...normalized.messages, ...Object.values(normalized.fields).flat()].join(' ') || t('listExport.error'))
    } finally {
      setPending(false)
    }
  }

  return <Dialog.Root open onOpenChange={(open) => { if (!open && !pending) onClose() }}>
    <Dialog.Portal>
      <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/45" />
      <Dialog.Viewport className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <Dialog.Popup finalFocus={returnFocus} className="w-full max-w-md rounded-lg border border-border bg-background p-6 text-foreground shadow-xl outline-none">
          <Dialog.Title className="text-lg font-semibold">{t('listExport.title')}</Dialog.Title>
          <form className="mt-4 grid gap-4" onSubmit={(event) => void submit(event)} aria-busy={pending}>
            {error && <Alert tone="danger">{error}</Alert>}
            <label className="grid gap-1 text-sm">{t('listExport.format')}
              <select className="h-9 rounded-md border border-input bg-background px-3" disabled={pending} value={format} onChange={(event) => setFormat(event.target.value as ListExportFormat)}>
                {formats.map((value) => <option key={value} value={value}>{t(`listExport.${value}`)}</option>)}
              </select>
            </label>
            <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{t(pending ? 'listExport.exporting' : 'listExport.download')}</Button></div>
          </form>
        </Dialog.Popup>
      </Dialog.Viewport>
    </Dialog.Portal>
  </Dialog.Root>
}
