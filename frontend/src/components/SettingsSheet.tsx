import { useEffect, useRef, useState, type RefObject } from 'react'
import { normalizeMutationError } from '../api/errors'
import type { SettingData, SettingValue } from '../api/settings'
import { useTranslation } from '../i18n/i18n'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './ui/sheet'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

type Props = {
  title: string
  description: string
  load: (signal: AbortSignal) => Promise<{ settings: SettingData[] }>
  save: (key: string, value: SettingValue) => Promise<SettingData>
  onClose: (changed: boolean) => void
  returnFocus: RefObject<HTMLElement | null>
}

export function SettingsSheet({ title, description, load, save, onClose, returnFocus }: Props) {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<SettingData[] | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [pendingKey, setPendingKey] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const changed = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then((result) => { setSettings(result.settings); setLoadError(false) }).catch(() => {
      if (!controller.signal.aborted) setLoadError(true)
    })
    return () => controller.abort()
  }, [load, retry])

  async function change(key: string, value: SettingValue) {
    if (pendingKey) return
    setPendingKey(key)
    setFieldErrors((current) => ({ ...current, [key]: '' }))
    try {
      const result = await save(key, value)
      changed.current = true
      setSettings((current) => current?.map((item) => item.key === key ? result : item) ?? null)
    } catch (cause) {
      const error = normalizeMutationError(cause)
      setFieldErrors((current) => ({ ...current, [key]: [...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('settings.saveError') }))
    } finally {
      setPendingKey(null)
    }
  }

  function close() { if (!pendingKey) onClose(changed.current) }

  return <Sheet open onOpenChange={(open) => { if (!open) close() }}>
    <SheetContent finalFocus={returnFocus}>
      <SheetHeader><SheetTitle>{title}</SheetTitle><SheetDescription>{description}</SheetDescription></SheetHeader>
      {loadError && <Alert tone="danger">{t('settings.loadError')} <Button variant="ghost" onClick={() => setRetry((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
      {!settings && !loadError && <p role="status">{t('common.loading')}</p>}
      {settings && <div className="divide-y divide-border">{settings.map((setting) => <SettingField key={setting.key} setting={setting} pending={pendingKey === setting.key} disabled={pendingKey !== null} error={fieldErrors[setting.key]} onChange={(value) => void change(setting.key, value)} />)}</div>}
      <div className="mt-6 flex justify-end"><Button type="button" variant="ghost" disabled={pendingKey !== null} onClick={close}>{t('common.close')}</Button></div>
    </SheetContent>
  </Sheet>
}

function SettingField({ setting, pending, disabled, error, onChange }: {
  setting: SettingData; pending: boolean; disabled: boolean; error?: string; onChange: (value: SettingValue) => void
}) {
  const { t } = useTranslation()
  const descriptionId = `setting-${setting.key}-description`
  return <div className="grid gap-2 py-4" aria-busy={pending}>
    <div className="flex items-start justify-between gap-4">
      <div className="grid gap-1"><label className="font-medium" htmlFor={`setting-${setting.key}`}>{setting.name}</label><p className="text-sm text-muted-foreground" id={descriptionId}>{setting.description}</p></div>
      {setting.type === 'boolean' && <input id={`setting-${setting.key}`} role="switch" type="checkbox" aria-describedby={descriptionId} className="mt-1 size-5 shrink-0 accent-primary" checked={setting.value === true} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />}
    </div>
    {setting.type === 'choice' && <select id={`setting-${setting.key}`} aria-describedby={descriptionId} className="h-9 w-full rounded-md border border-input bg-background px-3" value={String(setting.value)} disabled={disabled} onChange={(event) => onChange(event.target.value)}>{setting.choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</select>}
    {pending && <p role="status" className="text-sm text-muted-foreground">{t('settings.saving')}</p>}
    {error && <Alert tone="danger">{error}</Alert>}
  </div>
}
