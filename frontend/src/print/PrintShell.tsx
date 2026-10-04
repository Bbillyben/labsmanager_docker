import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { getPrintRenderer, type PrintRequest } from './registry'
import { registerBuiltinPrintRenderers } from './renderers'
import styles from './print.module.css'

registerBuiltinPrintRenderers()

export function PrintShell({ request, onClose }: { request: PrintRequest; onClose: () => void }) {
  const { t } = useTranslation()
  const [ready, setReady] = useState(false)
  const backButton = useRef<HTMLButtonElement | null>(null)
  const markReady = useCallback(() => setReady(true), [])
  useEffect(() => { backButton.current?.focus() }, [])
  const definition = getPrintRenderer(request.renderer)
  const page = request.page ?? definition?.defaultPage ?? { size: 'A4', orientation: 'landscape' }
  const Renderer = definition?.render
  return <main className={styles.shell} role="dialog" aria-modal="true" aria-label={request.title}>
    <style>{`@page { size: ${page.size} ${page.orientation}; margin: 12mm; }`}</style>
    <div className={styles.actions}>
      <Button ref={backButton} onClick={onClose} variant="ghost">{t('print.back')}</Button>
      <Button disabled={!ready || !Renderer} onClick={() => window.print()}>{t('print.action')}</Button>
    </div>
    <header className={styles.header}><h1>{request.title}</h1>{request.subtitle && <p>{request.subtitle}</p>}</header>
    {Renderer ? <Renderer state={request.state as never} onReady={markReady} /> : <p role="alert">{t('print.unknownRenderer')}</p>}
  </main>
}
