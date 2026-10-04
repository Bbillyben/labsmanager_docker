import { useCallback, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Pencil, Plus, Unlink } from 'lucide-react'
import { getAdminInvitations, getAdminNotifications, getAdminPlugin, getAdminPlugins, getAdminSettings, getAdminUsers, getEmployeeOptions, reloadAdminPlugins, removeExpiredAdminInvitations, runAdminNotificationAction, sendAdminInvitation, updateAdminPluginSetting, updateAdminSetting, updateAdminUserEmployee, type AdminUser, type PluginDetail } from '../api/adminSettings'
import type { UserSettingData } from '../api/userSettings'
import type { SettingValue } from '../api/settings'
import { normalizeMutationError } from '../api/errors'
import { EntityActionMenu } from '../components/EntityActionMenu'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { useEmployeeResource } from './useEmployeeResource'
import { SettingRow } from './SettingsHubPage'
import styles from './SettingsHubPage.module.css'

function errorText(error: unknown, fallback: string) {
  const parsed = normalizeMutationError(error)
  return [...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ') || fallback
}

function SettingList({ settings, onChange }: { settings: UserSettingData[]; onChange: (key: string, value: SettingValue) => Promise<UserSettingData> }) {
  const { t } = useTranslation()
  const [values, setValues] = useState(settings)
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<string | null>(null)
  async function save(key: string, value: SettingValue) {
    setPending(key); setSaved(null); setError((old) => ({ ...old, [key]: '' }))
    try {
      const result = await onChange(key, value)
      setValues((old) => old.map((row) => row.key === key ? result : row))
      setSaved(key)
      return result
    } catch (cause) { setError((old) => ({ ...old, [key]: errorText(cause, t('settings.saveError')) })); return null }
    finally { setPending(null) }
  }
  return <div>{values.map((setting) => <SettingRow key={setting.key} setting={setting} disabled={pending !== null} saving={pending === setting.key} saved={saved === setting.key} error={error[setting.key]} onSave={(value) => save(setting.key, value)} />)}</div>
}

export function AdminSettingsSection({ section, afterSave }: { section: 'general' | 'plugins'; afterSave?: () => void }) {
  const { t } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getAdminSettings(key as 'general' | 'plugins', signal), [])
  const resource = useEmployeeResource(section, loader)
  return <section className={styles.section}><h2>{t(`settingsAdmin.${section}`)}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <SettingList key={section} settings={resource.data.settings} onChange={async (key, value) => { const result = await updateAdminSetting(section, key, value); afterSave?.(); return result }} />}
  </section>
}

export function AdminUsersPage() {
  const { t, language } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getAdminUsers(signal), [])
  const optionsLoader = useCallback((_key: string, signal: AbortSignal) => getEmployeeOptions(signal), [])
  const users = useEmployeeResource('admin-users', loader)
  const options = useEmployeeResource('admin-employee-options', optionsLoader)
  const [editing, setEditing] = useState<AdminUser | null>(null)
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const focus = useRef<HTMLElement | null>(null)
  async function save(id: number, selected: number | null) {
    setPending(true); setError('')
    try { const updated = await updateAdminUserEmployee(id, selected); users.updateData((data) => ({ results: data.results.map((row) => row.id === id ? updated : row) })); options.retry(); setEditing(null) }
    catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }
  return <div className={styles.content}><section className={styles.section}><h2>{t('settingsAdmin.users')}</h2>
    {users.loading && <p role="status">{t('common.loading')}</p>}
    {!!users.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={users.retry}>{t('common.retry')}</Button></Alert>}
    {users.data && <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.username')}</th><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.linkedEmployee')}</th><th>{t('settingsAdmin.lastLogin')}</th><th>{t('settingsAdmin.action')}</th></tr></thead><tbody>
      {users.data.results.map((row) => <tr key={row.id}><td>{row.username}</td><td>{row.name || '—'}</td><td>{row.employee?.name || '—'}</td><td>{row.last_login ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.last_login)) : '—'}</td><td><EntityActionMenu label={t('common.actionsFor', { name: row.username })} onTrigger={(trigger) => { focus.current = trigger }} groups={[[
        { id: 'link', icon: <Pencil aria-hidden="true" />, label: t(row.employee ? 'settingsAdmin.changeEmployee' : 'settingsAdmin.linkEmployee'), onSelect: () => { setEditing(row); setEmployeeId(row.employee?.id ?? null); setError('') } },
        ...(row.employee ? [{ id: 'unlink', icon: <Unlink aria-hidden="true" />, label: t('settingsAdmin.unlinkEmployee'), onSelect: () => void save(row.id, null) }] : []),
      ]]} /></td></tr>)}
    </tbody></table></div>}
    {editing && <Sheet open onOpenChange={(open) => { if (!open && !pending) setEditing(null) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t(editing.employee ? 'settingsAdmin.changeEmployee' : 'settingsAdmin.linkEmployee')}</SheetTitle><SheetDescription>{editing.username}</SheetDescription></SheetHeader>
      <form className={styles.form} onSubmit={(event) => { event.preventDefault(); void save(editing.id, employeeId) }}><label>{t('settingsAdmin.linkedEmployee')}<select className={styles.select} value={employeeId ?? ''} onChange={(event) => setEmployeeId(event.target.value ? Number(event.target.value) : null)}><option value="">—</option>{editing.employee && <option value={editing.employee.id}>{editing.employee.name}</option>}{options.data?.results.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>
        {error && <Alert tone="danger">{error}</Alert>}{!!options.error && <Alert tone="danger">{t('settings.loadError')}</Alert>}
        <div className={styles.sheetActions}><Button type="button" variant="ghost" onClick={() => setEditing(null)}>{t('common.close')}</Button><Button type="submit" disabled={pending || !options.data}>{t('common.save')}</Button></div>
      </form></SheetContent></Sheet>}
    {error && !editing && <Alert tone="danger">{error}</Alert>}
  </section><AdminInvitationsSection /></div>
}

function AdminInvitationsSection() {
  const { t, language } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getAdminInvitations(signal), [])
  const invitations = useEmployeeResource('admin-invitations', loader)
  const [inviting, setInviting] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [email, setEmail] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const focus = useRef<HTMLElement | null>(null)
  async function send() {
    setPending(true); setError(''); setFeedback('')
    try {
      const created = await sendAdminInvitation(email)
      invitations.updateData((data) => ({ results: [created, ...data.results] }))
      setInviting(false); setEmail(''); setFeedback(t('settingsAdmin.invitationSent'))
      await invitations.refresh()
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }
  async function removeExpired() {
    setPending(true); setError(''); setFeedback('')
    try {
      const result = await removeExpiredAdminInvitations()
      setConfirmRemove(false); setFeedback(t('settingsAdmin.expiredRemoved', { count: result.deleted }))
      await invitations.refresh()
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }
  const date = (value: string | null) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
  return <section className={styles.section} aria-label={t('settingsAdmin.invitations')}><div className={styles.heading}><h3>{t('settingsAdmin.invitations')}</h3><div className={styles.actions}>
    <Button variant="secondary" disabled={pending} onClick={(event) => { focus.current = event.currentTarget; setInviting(true); setError('') }}><Plus aria-hidden="true" />{t('settingsAdmin.inviteUser')}</Button>
    <Button variant="destructive" disabled={pending} onClick={(event) => { focus.current = event.currentTarget; setConfirmRemove(true); setError('') }}>{t('settingsAdmin.removeExpired')}</Button>
  </div></div>
    {feedback && <p role="status" className={styles.feedback}>{feedback}</p>}
    {error && !inviting && !confirmRemove && <Alert tone="danger">{error}</Alert>}
    {invitations.loading && <p role="status">{t('common.loading')}</p>}
    {!!invitations.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={invitations.retry}>{t('common.retry')}</Button></Alert>}
    {invitations.data && <div className={styles.tableScroll}><table className={`${styles.table} ${styles.invitationTable}`}><thead><tr><th>{t('settingsAdmin.email')}</th><th>{t('settingsAdmin.dateCreated')}</th><th>{t('settingsAdmin.dateSent')}</th><th>{t('settingsAdmin.accepted')}</th><th>{t('settingsAdmin.keyExpired')}</th><th>{t('settingsAdmin.inviter')}</th></tr></thead><tbody>
      {invitations.data.results.map((row) => <tr key={row.id}><td>{row.email}</td><td>{date(row.created)}</td><td>{date(row.sent)}</td><td><Badge variant={row.accepted ? 'secondary' : 'outline'}>{t(row.accepted ? 'settingsAdmin.yes' : 'settingsAdmin.no')}</Badge></td><td><Badge variant={row.key_expired ? 'secondary' : 'outline'}>{t(row.key_expired ? 'settingsAdmin.yes' : 'settingsAdmin.no')}</Badge></td><td>{row.inviter?.username || '—'}</td></tr>)}
    </tbody></table>{!invitations.data.results.length && <p className={styles.empty}>{t('settingsAdmin.noInvitations')}</p>}</div>}
    {inviting && <Sheet open onOpenChange={(open) => { if (!open && !pending) setInviting(false) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t('settingsAdmin.inviteUser')}</SheetTitle><SheetDescription>{t('settingsAdmin.inviteDescription')}</SheetDescription></SheetHeader><form className={styles.form} onSubmit={(event) => { event.preventDefault(); void send() }}><label>{t('settingsAdmin.email')}<Input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{error && <Alert tone="danger">{error}</Alert>}<div className={styles.sheetActions}><Button type="button" variant="ghost" disabled={pending} onClick={() => setInviting(false)}>{t('common.close')}</Button><Button type="submit" disabled={pending}>{pending ? t('settingsAdmin.sending') : t('settingsAdmin.sendInvitation')}</Button></div></form></SheetContent></Sheet>}
    {confirmRemove && <ConfirmDialog title={t('settingsAdmin.removeExpired')} description={t('settingsAdmin.removeExpiredDescription')} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} onCancel={() => { setConfirmRemove(false); setError('') }} onConfirm={() => void removeExpired()} returnFocus={focus} />}
  </section>
}

export function AdminNotificationsPage() {
  const { t, language } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getAdminNotifications(signal), [])
  const resource = useEmployeeResource('admin-notifications', loader)
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function run(action: 'check' | 'send') {
    setPending(true); setError(''); setMessage('')
    try {
      const result = await runAdminNotificationAction(action)
      resource.updateData(() => ({ results: result.results }))
      setMessage(action === 'send' ? t('settingsAdmin.sentCount', { count: result.sent ?? 0 }) : t('settingsAdmin.checkedCount', { count: Object.values(result.counts ?? {}).reduce((sum, count) => sum + count, 0) }))
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(false) }
  }
  return <section className={styles.section}><div className={styles.heading}><h3>{t('settingsAdmin.notifications')}</h3><div className={styles.actions}><Button disabled={pending} onClick={() => void run('check')}>{t('settingsAdmin.checkNotifications')}</Button><Button disabled={pending} onClick={() => void run('send')}>{t('settingsAdmin.sendPending')}</Button></div></div>
    {message && <p role="status">{message}</p>}{error && <Alert tone="danger">{error}</Alert>}
    {resource.loading && <p role="status">{t('common.loading')}</p>}{!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.username')}</th><th>{t('settingsAdmin.source')}</th><th>{t('settingsAdmin.action')}</th><th>{t('settingsAdmin.object')}</th><th>{t('settingsAdmin.created')}</th></tr></thead><tbody>{resource.data.results.map((row) => <tr key={row.id}><td>{row.user}</td><td>{row.source_type}</td><td>{row.action}</td><td>{row.object}</td><td>{new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.created))}</td></tr>)}</tbody></table>{!resource.data.results.length && <p className={styles.empty}>{t('settingsAdmin.noPending')}</p>}</div>}
  </section>
}

export function AdminPluginsPage() {
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getAdminPlugins(signal), [])
  const resource = useEmployeeResource('admin-plugins', loader)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  async function reload() { setPending(true); setError(''); try { const result = await reloadAdminPlugins(); resource.updateData(() => result) } catch (cause) { setError(errorText(cause, t('settings.saveError'))) } finally { setPending(false) } }
  return <div className={styles.content}><AdminSettingsSection section="plugins" afterSave={resource.retry} /><section className={styles.section}><div className={styles.heading}><h3>{t('settingsAdmin.plugins')}</h3><Button disabled={pending} onClick={() => void reload()}>{t('settingsAdmin.reloadPlugins')}</Button></div>
    {error && <Alert tone="danger">{error}</Alert>}{resource.loading && <p role="status">{t('common.loading')}</p>}{!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.plugin')}</th><th>{t('settingsAdmin.description')}</th><th>{t('settingsAdmin.mixins')}</th><th>{t('settingsAdmin.version')}</th><th>{t('settingsAdmin.author')}</th></tr></thead><tbody>{resource.data.results.map((row) => <tr key={row.key}><td><Link to={`/settings/admin/plugins/${encodeURIComponent(row.key)}`}>{row.human_name}</Link></td><td>{row.description}</td><td>{row.mixins.join(', ')}</td><td>{row.version || '—'}</td><td>{row.author}</td></tr>)}</tbody></table></div>}
    {!!resource.data?.errors.length && <section className={styles.section}><h2>{t('settingsAdmin.pluginErrors')}</h2><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.stage')}</th><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.message')}</th></tr></thead><tbody>{resource.data.errors.map((row, index) => <tr key={`${row.stage}-${row.name}-${index}`}><td>{row.stage}</td><td>{row.name}</td><td>{row.message}</td></tr>)}</tbody></table></div></section>}
  </section></div>
}

export function AdminPluginDetailPage() {
  const { pluginKey = '' } = useParams()
  const { t, language } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getAdminPlugin(key, signal), [])
  const resource = useEmployeeResource(pluginKey, loader)
  const data: PluginDetail | null = resource.data
  return <div className={styles.content}><Link to="/settings/admin/plugins">← {t('settingsAdmin.plugins')}</Link>
    {resource.loading && <p role="status">{t('common.loading')}</p>}{!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {data && <><section className={styles.section}><h2>{data.human_name}</h2><dl className={styles.facts}>{([
      ['description', data.description], ['author', data.author], ['version', data.version], ['published', data.pub_date ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(new Date(data.pub_date)) : null], ['website', data.website], ['license', data.license], ['mixins', data.mixins.join(', ')],
    ] as const).map(([label, value]) => <div key={label}><dt>{t(`settingsAdmin.${label}`)}</dt><dd>{label === 'website' && value ? <a href={value} target="_blank" rel="noreferrer">{value}</a> : value || '—'}</dd></div>)}</dl></section>
      {data.sections.settings && <section className={styles.section}><h2>{t('settingsAdmin.settings')}</h2><SettingList key={pluginKey} settings={data.sections.settings} onChange={(key, value) => updateAdminPluginSetting(pluginKey, key, value)} /></section>}
      {data.sections.schedule && <section className={styles.section}><h2>{t('settingsAdmin.schedule')}</h2><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.function')}</th><th>{t('settingsAdmin.scheduleType')}</th><th>{t('settingsAdmin.repeat')}</th><th>{t('settingsAdmin.nextRun')}</th><th>{t('settingsAdmin.success')}</th></tr></thead><tbody>{data.sections.schedule.map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.function}</td><td>{row.schedule_type}</td><td>{row.repeat ?? '—'}</td><td>{row.next_run ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.next_run)) : '—'}</td><td>{row.success ? '✓' : '—'}</td></tr>)}</tbody></table></div></section>}
      {data.sections.urls && <section className={styles.section}><h2>{t('settingsAdmin.urls')}</h2><p>{t('settingsAdmin.baseUrl')}: {data.sections.urls.base_url}</p><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.url')}</th><th>{t('settingsAdmin.action')}</th></tr></thead><tbody>{data.sections.urls.routes.map((row) => <tr key={`${row.name}-${row.url}`}><td>{row.name}</td><td>{row.url}</td><td>{row.href && <a href={row.href} target="_blank" rel="noreferrer">{t('settingsAdmin.openNewTab')}</a>}</td></tr>)}</tbody></table></div></section>}
    </>}
  </div>
}
