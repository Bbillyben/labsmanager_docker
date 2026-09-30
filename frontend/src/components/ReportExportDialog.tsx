import { Dialog } from '@base-ui/react/dialog'
import { useEffect, useState, type FormEvent, type RefObject } from 'react'
import { exportReport, getReportTemplates, type ReportEntity, type ReportFormat, type ReportTemplate } from '../api/reports'
import { normalizeMutationError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

function initialDates() {
  const today = new Date()
  const lastYear = new Date(today.getFullYear() - 1, today.getMonth(), Math.min(today.getDate(), new Date(today.getFullYear() - 1, today.getMonth() + 1, 0).getDate()))
  const date = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  return { start: date(lastYear), end: date(today) }
}

export function ReportExportDialog({ entity, id, format, title, timeframe, returnFocus, onClose }: {
  entity: ReportEntity; id: number; format: ReportFormat; title: string; timeframe: boolean
  returnFocus: RefObject<HTMLElement | null>; onClose: () => void
}) {
  const { t } = useTranslation()
  const [templates, setTemplates] = useState<ReportTemplate[] | null>(null)
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dates, setDates] = useState(initialDates)

  useEffect(() => {
    const controller = new AbortController()
    getReportTemplates(entity, id, format, controller.signal).then((result) => {
      setTemplates(result.templates)
      setTemplateId(result.templates[0]?.id ?? null)
    }).catch(() => { if (!controller.signal.aborted) setLoadError(true) })
    return () => controller.abort()
  }, [entity, id, format])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (templateId === null || pending) return
    if (timeframe && dates.start && dates.end && dates.start > dates.end) {
      setError(t('reports.dateOrderError'))
      return
    }
    setPending(true)
    setError(null)
    try {
      const file = await exportReport(entity, id, format, {
        template_id: templateId,
        ...(timeframe ? { start_date: dates.start || null, end_date: dates.end || null } : {}),
      })
      const url = URL.createObjectURL(file.blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = file.filename ?? `report.${format === 'word' ? 'docx' : 'pdf'}`
      anchor.style.display = 'none'
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      onClose()
    } catch (cause) {
      const normalized = normalizeMutationError(cause)
      setError([...normalized.messages, ...Object.values(normalized.fields).flat()].join(' ') || t('reports.exportError'))
    } finally {
      setPending(false)
    }
  }

  return <Dialog.Root open onOpenChange={(open) => { if (!open && !pending) onClose() }}>
    <Dialog.Portal>
      <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/45" />
      <Dialog.Viewport className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <Dialog.Popup finalFocus={returnFocus} className="w-full max-w-md rounded-lg border border-border bg-background p-6 text-foreground shadow-xl outline-none">
          <Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title>
          <Dialog.Description className="mb-4 text-sm text-muted-foreground">{t('reports.chooseTemplate')}</Dialog.Description>
          <form className="grid gap-4" onSubmit={(event) => void submit(event)} aria-busy={pending}>
            {loadError && <Alert tone="danger">{t('reports.templatesError')}</Alert>}
            {error && <Alert tone="danger">{error}</Alert>}
            <label className="grid gap-1 text-sm">{t('reports.template')}
              <select className="h-9 rounded-md border border-input bg-background px-3" required disabled={pending || !templates?.length} value={templateId ?? ''} onChange={(event) => setTemplateId(Number(event.target.value))}>
                {!templates?.length && <option value="">{templates ? t('reports.noTemplates') : t('common.loading')}</option>}
                {templates?.map((template) => <option value={template.id} key={template.id}>{template.name}</option>)}
              </select>
            </label>
            {timeframe && <>
              <label className="grid gap-1 text-sm">{t('reports.from')}<input className="h-9 rounded-md border border-input bg-background px-3" type="date" disabled={pending} value={dates.start} onChange={(event) => setDates((current) => ({ ...current, start: event.target.value }))} /></label>
              <label className="grid gap-1 text-sm">{t('reports.to')}<input className="h-9 rounded-md border border-input bg-background px-3" type="date" disabled={pending} value={dates.end} onChange={(event) => setDates((current) => ({ ...current, end: event.target.value }))} /></label>
            </>}
            <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={pending || templateId === null}>{t(pending ? 'reports.exporting' : 'reports.export')}</Button></div>
          </form>
        </Dialog.Popup>
      </Dialog.Viewport>
    </Dialog.Portal>
  </Dialog.Root>
}
