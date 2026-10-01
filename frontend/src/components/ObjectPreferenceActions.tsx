import { Bell, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getObjectPreferences, setObjectPreference, type PreferenceStatus, type PreferenceType } from '../api/preferences'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'

export function ObjectPreferenceActions({ type, objectId }: { type: PreferenceType; objectId: number | string }) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<PreferenceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<keyof PreferenceStatus | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    getObjectPreferences(type, objectId, controller.signal).then(
      (next) => { if (!controller.signal.aborted) { setStatus(next); setLoading(false); setError(false) } },
      () => { if (!controller.signal.aborted) { setLoading(false); setError(true) } },
    )
    return () => controller.abort()
  }, [type, objectId])
  async function change(kind: keyof PreferenceStatus) {
    if (!status || pending) return
    const previous = status
    setStatus({ ...status, [kind]: !status[kind] })
    setPending(kind)
    setError(false)
    try { setStatus(await setObjectPreference(type, objectId, { [kind]: !status[kind] })) }
    catch { setStatus(previous); setError(true) }
    finally { setPending(null) }
  }
  return <div className="flex items-center gap-1" aria-busy={loading || Boolean(pending)}>
    <Button size="icon-sm" variant="ghost" type="button" disabled={loading || !status || Boolean(pending)} aria-pressed={Boolean(status?.favorite)} aria-label={t(status?.favorite ? 'preferences.removeFavorite' : 'preferences.addFavorite')} onClick={() => void change('favorite')}><Star aria-hidden="true" fill={status?.favorite ? 'currentColor' : 'none'} /></Button>
    <Button size="icon-sm" variant="ghost" type="button" disabled={loading || !status || Boolean(pending)} aria-pressed={Boolean(status?.subscription)} aria-label={t(status?.subscription ? 'preferences.unsubscribe' : 'preferences.subscribe')} onClick={() => void change('subscription')}><Bell aria-hidden="true" fill={status?.subscription ? 'currentColor' : 'none'} /></Button>
    {error && <span role="alert" className="text-xs text-destructive">{t('preferences.error')}</span>}
  </div>
}
