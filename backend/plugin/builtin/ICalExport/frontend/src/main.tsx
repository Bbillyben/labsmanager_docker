import { useRef, useState } from 'react'
import { Alert, Button, Input, Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, apiRequest, copyPluginToken, registerPluginTranslations, usePluginTranslation } from '@labsmanager/plugin-ui'
import fr from './locales/fr.json'
import en from './locales/en.json'

registerPluginTranslations('icalexport', { fr, en })

type Context = { name?: string; actionUrl?: string; options?: string[] }

export function SubscriptionDialog({ context, onClose }: { context: Context; onClose?: () => void }) {
  const { t } = usePluginTranslation('icalexport')
  const [assigned, setAssigned] = useState(false)
  const [url, setUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const supportsAssigned = context.options?.includes('assigned_to_me') ?? false

  async function generate() {
    if (!context.actionUrl) { setError(true); return }
    setPending(true); setError(false); setCopied(false); setUrl('')
    try {
      const result = await apiRequest<{ url: string }>(context.actionUrl, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(supportsAssigned && assigned ? { assigned_to_me: true } : {}),
      })
      setUrl(result.url)
    } catch { setError(true) }
    finally { setPending(false) }
  }

  async function copy() {
    if (input.current && await copyPluginToken(input.current)) setCopied(true)
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !pending) onClose?.() }}>
    <SheetContent>
      <SheetHeader>
        <SheetTitle>{t('title')}</SheetTitle>
        <SheetDescription>{context.name || t('calendar')}</SheetDescription>
      </SheetHeader>
      <div className="grid gap-4">
        {supportsAssigned && <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={assigned} onChange={(event) => { setAssigned(event.target.checked); setUrl(''); setCopied(false) }} />
          {t('assignedOnly')}
        </label>}
        <Button variant="primary" disabled={pending} onClick={() => void generate()}>
          {pending ? t('creating') : t('createLink')}
        </Button>
        {error && <Alert tone="danger">{t('createError')}</Alert>}
        {url && <div className="grid gap-2">
          <label className="text-sm" htmlFor="ical-subscription-url">{t('subscriptionLink')}</label>
          <Input id="ical-subscription-url" ref={input} readOnly value={url} onFocus={(event) => event.currentTarget.select()} />
          <Button onClick={() => void copy()}>{t('copy')}</Button>
          {copied && <span role="status" className="text-sm text-muted-foreground">{t('copied')}</span>}
        </div>}
      </div>
    </SheetContent>
  </Sheet>
}
