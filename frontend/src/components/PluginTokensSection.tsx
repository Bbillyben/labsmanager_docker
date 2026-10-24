import { Plus, Pencil, Trash2 } from 'lucide-react'
import { useCallback, useRef, useState, type FormEvent } from 'react'
import { createPluginToken, getPluginTokens, renamePluginToken, revokePluginToken, type PluginToken, type PluginTokenKind } from '../api/pluginPersonal'
import { normalizeMutationError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { useEmployeeResource } from '../pages/useEmployeeResource'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Input } from './ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from './ui/sheet'
import { ConfirmDialog } from './common/ConfirmDialog'
import { copyPluginToken } from './copyPluginToken'
import styles from './PluginTokensSection.module.css'

function errorText(error: unknown, fallback: string) {
  const parsed = normalizeMutationError(error)
  return [...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ') || fallback
}

export function PluginTokensSection({ pluginKey, kind }: { pluginKey: string; kind: PluginTokenKind }) {
  const { t, language } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getPluginTokens(pluginKey, kind, signal), [pluginKey, kind])
  const resource = useEmployeeResource(`${pluginKey}:${kind}`, loader)
  const [editing, setEditing] = useState<PluginToken | 'new' | null>(null)
  const [revoke, setRevoke] = useState<PluginToken | null>(null)
  const [secret, setSecret] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [scopes, setScopes] = useState<string[]>([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [copied, setCopied] = useState(false)
  const focus = useRef<HTMLElement | null>(null)
  const secretInput = useRef<HTMLInputElement | null>(null)
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'

  function openForm(value: PluginToken | 'new', trigger: HTMLElement) {
    focus.current = trigger
    setEditing(value)
    setName(value === 'new' ? '' : value.name)
    setExpiresAt('')
    setScopes([])
    setError('')
    setFeedback('')
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!editing || pending) return
    if (!name.trim()) { setError(t('pluginTokens.nameRequired')); return }
    let expiry: string | null = null
    if (editing === 'new' && expiresAt) {
      const timestamp = new Date(expiresAt).getTime()
      if (!Number.isFinite(timestamp) || timestamp <= Date.now()) { setError(t('pluginTokens.futureExpiration')); return }
      expiry = new Date(timestamp).toISOString()
    }
    setPending(true); setError('')
    try {
      if (editing === 'new') {
        const { token, ...created } = await createPluginToken(pluginKey, kind, name.trim(), scopes, expiry)
        resource.updateData((old) => ({ ...old, tokens: [created, ...old.tokens] }))
        setEditing(null)
        setSecret(token)
        setCopied(false)
      } else {
        const updated = await renamePluginToken(pluginKey, kind, editing.public_id, name.trim())
        resource.updateData((old) => ({ ...old, tokens: old.tokens.map((row) => row.public_id === updated.public_id ? updated : row) }))
        setEditing(null)
        setFeedback(t('pluginTokens.renamed'))
      }
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }

  async function confirmRevoke() {
    if (!revoke || pending) return
    setPending(true); setError('')
    try {
      const updated = await revokePluginToken(pluginKey, kind, revoke.public_id)
      resource.updateData((old) => ({ ...old, tokens: old.tokens.map((row) => row.public_id === updated.public_id ? updated : row) }))
      setRevoke(null)
      setFeedback(t('pluginTokens.revoked'))
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }

  async function copySecret() {
    if (!secretInput.current) return
    const success = await copyPluginToken(secretInput.current)
    setCopied(success)
  }

  const scopeOptions = resource.data?.scopes ?? []
  const status = (row: PluginToken) => row.revoked_at ? t('pluginTokens.revokedStatus') : row.expires_at && new Date(row.expires_at).getTime() <= Date.now() ? t('pluginTokens.expiredStatus') : t('pluginTokens.activeStatus')

  return <section className={styles.section} aria-label={t(kind === 'plugin' ? 'pluginTokens.adminTitle' : 'pluginTokens.userTitle')}>
    <div className={styles.heading}><h2>{t(kind === 'plugin' ? 'pluginTokens.adminTitle' : 'pluginTokens.userTitle')}</h2><Button variant="secondary" onClick={(event) => openForm('new', event.currentTarget)} disabled={pending || !resource.data}><Plus aria-hidden="true" />{t('pluginTokens.create')}</Button></div>
    {feedback && <p role="status" className={styles.feedback}>{feedback}</p>}
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('pluginTokens.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <div className={styles.list}>{resource.data.tokens.length === 0 && <p className={styles.muted}>{t('pluginTokens.empty')}</p>}{resource.data.tokens.map((row) => <div className={styles.row} key={row.public_id}>
      <div className={styles.identity}><strong>{row.name}</strong><code>{row.public_id}</code><span>{status(row)}</span>{row.scopes.length > 0 && <small>{row.scopes.join(', ')}</small>}</div>
      <dl className={styles.dates}><div><dt>{t('pluginTokens.created')}</dt><dd>{date(row.created_at)}</dd></div><div><dt>{t('pluginTokens.expires')}</dt><dd>{date(row.expires_at)}</dd></div><div><dt>{t('pluginTokens.lastUsed')}</dt><dd>{date(row.last_used_at)}</dd></div></dl>
      {!row.revoked_at && <div className={styles.actions}><Button variant="ghost" onClick={(event) => openForm(row, event.currentTarget)}><Pencil aria-hidden="true" />{t('pluginTokens.rename')}</Button><Button variant="ghost" onClick={(event) => { focus.current = event.currentTarget; setError(''); setRevoke(row) }}><Trash2 aria-hidden="true" />{t('pluginTokens.revoke')}</Button></div>}
    </div>)}</div>}

    <Sheet open={editing !== null} onOpenChange={(open) => { if (!open && !pending) setEditing(null) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t(editing === 'new' ? 'pluginTokens.create' : 'pluginTokens.rename')}</SheetTitle><SheetDescription>{t('pluginTokens.formDescription')}</SheetDescription></SheetHeader>
      <form className={styles.form} onSubmit={(event) => void save(event)}><label>{t('pluginTokens.name')}<Input value={name} maxLength={150} onChange={(event) => setName(event.target.value)} required /></label>
        {editing === 'new' && <><label>{t('pluginTokens.expiresOptional')}<Input type="datetime-local" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} /></label>
          {scopeOptions.length > 0 && <fieldset className={styles.scopes}><legend>{t('pluginTokens.scopes')}</legend>{scopeOptions.map((scope) => <label key={scope.name}><input type="checkbox" checked={scopes.includes(scope.name)} onChange={(event) => setScopes((current) => event.target.checked ? [...current, scope.name] : current.filter((name) => name !== scope.name))} /><span>{scope.label}{scope.description && <small>{scope.description}</small>}</span></label>)}</fieldset>}</>}
        {error && <Alert tone="danger">{error}</Alert>}<div className={styles.actions}><Button type="button" variant="ghost" disabled={pending} onClick={() => setEditing(null)}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{pending ? t('common.saving') : t('common.save')}</Button></div>
      </form></SheetContent></Sheet>

    <Sheet open={secret !== null} onOpenChange={(open) => { if (!open) { setSecret(null); setCopied(false) } }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t('pluginTokens.secretTitle')}</SheetTitle><SheetDescription>{t('pluginTokens.secretOnce')}</SheetDescription></SheetHeader>
      <div className={styles.form}><Input ref={secretInput} readOnly value={secret ?? ''} aria-label={t('pluginTokens.secretTitle')} onFocus={(event) => event.currentTarget.select()} /><div className={styles.actions}><Button variant="secondary" onClick={() => void copySecret()}>{t('pluginTokens.copy')}</Button><Button variant="ghost" onClick={() => { setSecret(null); setCopied(false) }}>{t('common.close')}</Button></div>{copied && <p role="status" className={styles.feedback}>{t('pluginTokens.copied')}</p>}{!copied && <p className={styles.muted}>{t('pluginTokens.manualCopy')}</p>}</div>
    </SheetContent></Sheet>

    {revoke && <ConfirmDialog title={t('pluginTokens.revoke')} description={t('pluginTokens.confirmRevoke', { name: revoke.name })} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} onCancel={() => { setRevoke(null); setError('') }} onConfirm={() => void confirmRevoke()} returnFocus={focus} confirmLabel={t('pluginTokens.revoke')} destructive />}
  </section>
}
