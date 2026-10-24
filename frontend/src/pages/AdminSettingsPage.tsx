import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Pencil, Plus, Unlink } from 'lucide-react'
import { getAdminInvitations, getAdminNotifications, getAdminPlugin, getAdminPlugins, getAdminSettings, getAdminUsers, getEmployeeOptions, installAdminPluginDependencies, reloadAdminPlugins, removeExpiredAdminInvitations, runAdminNotificationAction, sendAdminInvitation, setAdminPluginActive, updateAdminInvitation, updateAdminPluginSetting, updateAdminSetting, updateAdminUserEmployee, type AdminInvitation, type AdminUser, type PluginDetail, type PluginSummary } from '../api/adminSettings'
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
import { SettingList } from '../components/SettingList'
import { PluginTokensSection } from '../components/PluginTokensSection'
import styles from './SettingsHubPage.module.css'

function errorText(error: unknown, fallback: string) {
  const parsed = normalizeMutationError(error)
  return [...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ') || fallback
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
  </section><AdminInvitationsSection employees={options.data?.results ?? []} /></div>
}

function AdminInvitationsSection({ employees }: { employees: { id: number; name: string }[] }) {
  const { t, language } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => getAdminInvitations(signal), [])
  const invitations = useEmployeeResource('admin-invitations', loader)
  const [inviting, setInviting] = useState(false)
  const [editingInvitation, setEditingInvitation] = useState<AdminInvitation | null>(null)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [email, setEmail] = useState('')
  const [invitationEmployeeId, setInvitationEmployeeId] = useState<number | null>(null)
  const [invitationGroupIds, setInvitationGroupIds] = useState<number[]>([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const focus = useRef<HTMLElement | null>(null)
  function openInvitation(row?: AdminInvitation) {
    setEditingInvitation(row ?? null)
    setEmail(row?.email ?? '')
    setInvitationEmployeeId(row?.employee?.id ?? null)
    setInvitationGroupIds(row?.group_ids ?? [])
    setError('')
    setInviting(true)
  }
  async function send() {
    setPending(true); setError(''); setFeedback('')
    try {
      if (editingInvitation) {
        const updated = await updateAdminInvitation(editingInvitation.id, invitationEmployeeId, invitations.data?.can_assign_groups ? invitationGroupIds : null)
        invitations.updateData((data) => ({ ...data, results: data.results.map((row) => row.id === updated.id ? updated : row) }))
        setFeedback(t('settingsAdmin.invitationUpdated'))
      } else {
        const created = await sendAdminInvitation(email, invitationEmployeeId, invitations.data?.can_assign_groups ? invitationGroupIds : null)
        invitations.updateData((data) => ({ ...data, results: [created, ...data.results] }))
        setFeedback(t('settingsAdmin.invitationSent'))
      }
      setInviting(false); setEditingInvitation(null); setEmail(''); setInvitationEmployeeId(null); setInvitationGroupIds([])
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
    <Button variant="secondary" disabled={pending} onClick={(event) => { focus.current = event.currentTarget; openInvitation() }}><Plus aria-hidden="true" />{t('settingsAdmin.inviteUser')}</Button>
    <Button variant="destructive" disabled={pending} onClick={(event) => { focus.current = event.currentTarget; setConfirmRemove(true); setError('') }}>{t('settingsAdmin.removeExpired')}</Button>
  </div></div>
    {feedback && <p role="status" className={styles.feedback}>{feedback}</p>}
    {error && !inviting && !confirmRemove && <Alert tone="danger">{error}</Alert>}
    {invitations.loading && <p role="status">{t('common.loading')}</p>}
    {!!invitations.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={invitations.retry}>{t('common.retry')}</Button></Alert>}
    {invitations.data && <div className={styles.tableScroll}><table className={`${styles.table} ${styles.invitationTable}`}><thead><tr><th>{t('settingsAdmin.email')}</th><th>{t('settingsAdmin.dateCreated')}</th><th>{t('settingsAdmin.dateSent')}</th><th>{t('settingsAdmin.accepted')}</th><th>{t('settingsAdmin.keyExpired')}</th><th>{t('settingsAdmin.inviter')}</th><th>{t('settingsAdmin.linkedEmployee')}</th><th>{t('settingsAdmin.groups')}</th><th>{t('settingsAdmin.action')}</th></tr></thead><tbody>
      {invitations.data.results.map((row) => <tr key={row.id}><td>{row.email}</td><td>{date(row.created)}</td><td>{date(row.sent)}</td><td><Badge variant={row.accepted ? 'secondary' : 'outline'}>{t(row.accepted ? 'settingsAdmin.yes' : 'settingsAdmin.no')}</Badge></td><td><Badge variant={row.key_expired ? 'secondary' : 'outline'}>{t(row.key_expired ? 'settingsAdmin.yes' : 'settingsAdmin.no')}</Badge></td><td>{row.inviter?.username || '—'}</td><td>{row.employee?.name || '—'}</td><td>{row.group_ids?.length || '—'}</td><td>{!row.accepted && !row.key_expired && <EntityActionMenu label={t('common.actionsFor', { name: row.email })} onTrigger={(trigger) => { focus.current = trigger }} groups={[[{ id: 'edit', icon: <Pencil aria-hidden="true" />, label: t('settingsAdmin.editProvisioning'), onSelect: () => openInvitation(row) }]]} />}</td></tr>)}
    </tbody></table>{!invitations.data.results.length && <p className={styles.empty}>{t('settingsAdmin.noInvitations')}</p>}</div>}
    {inviting && <Sheet open onOpenChange={(open) => { if (!open && !pending) setInviting(false) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{t(editingInvitation ? 'settingsAdmin.editProvisioning' : 'settingsAdmin.inviteUser')}</SheetTitle><SheetDescription>{t('settingsAdmin.inviteDescription')}</SheetDescription></SheetHeader><form className={styles.form} onSubmit={(event) => { event.preventDefault(); void send() }}><label>{t('settingsAdmin.email')}<Input type="email" required readOnly={!!editingInvitation} value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>{t('settingsAdmin.linkedEmployee')}<select className={styles.select} value={invitationEmployeeId ?? ''} onChange={(event) => setInvitationEmployeeId(event.target.value ? Number(event.target.value) : null)}><option value="">—</option>{editingInvitation?.employee && !employees.some((row) => row.id === editingInvitation.employee?.id) && <option value={editingInvitation.employee.id}>{editingInvitation.employee.name}</option>}{employees.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>{invitations.data?.can_assign_groups && <label>{t('settingsAdmin.groups')}<select className={styles.select} multiple size={Math.min(5, Math.max(2, invitations.data.group_options?.length ?? 0))} value={invitationGroupIds.map(String)} onChange={(event) => setInvitationGroupIds(Array.from(event.target.selectedOptions, (option) => Number(option.value)))}>{invitations.data.group_options?.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>}{error && <Alert tone="danger">{error}</Alert>}<div className={styles.sheetActions}><Button type="button" variant="ghost" disabled={pending} onClick={() => setInviting(false)}>{t('common.close')}</Button><Button type="submit" disabled={pending}>{pending ? t('settingsAdmin.sending') : t(editingInvitation ? 'common.save' : 'settingsAdmin.sendInvitation')}</Button></div></form></SheetContent></Sheet>}
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
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [confirm, setConfirm] = useState<PluginSummary | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  async function reload() { setPending('reload'); setError(''); setMessage(''); try { const result = await reloadAdminPlugins(); resource.updateData(() => result) } catch (cause) { setError(errorText(cause, t('settings.saveError'))) } finally { setPending(null) } }
  async function changeState(row: PluginSummary) {
    setPending(row.key); setError(''); setMessage('')
    try {
      await setAdminPluginActive(row.key, !row.active)
      const result = await getAdminPlugins(new AbortController().signal)
      resource.updateData(() => result)
      const updated = result.results.find((item) => item.key === row.key)
      if (!updated || updated.active === row.active) throw new Error(t('settingsAdmin.pluginStateError'))
      setConfirm(null)
      setMessage(t(updated.active ? 'settingsAdmin.pluginActivated' : 'settingsAdmin.pluginDeactivated'))
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(null) }
  }
  return <div className={styles.content}><AdminSettingsSection section="plugins" afterSave={resource.retry} /><section className={styles.section}><div className={styles.heading}><h3>{t('settingsAdmin.plugins')}</h3><Button disabled={pending !== null} onClick={() => void reload()}>{t('settingsAdmin.reloadPlugins')}</Button></div>
    {message && <p role="status">{message}</p>}{error && !confirm && <Alert tone="danger">{error}</Alert>}{resource.loading && <p role="status">{t('common.loading')}</p>}{!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {resource.data && <div className={styles.tableScroll}><table className={`${styles.table} ${styles.pluginTable}`}><thead><tr><th>{t('settingsAdmin.plugin')}</th><th>{t('settingsAdmin.description')}</th><th>{t('settingsAdmin.mixins')}</th><th>{t('settingsAdmin.version')}</th><th>{t('settingsAdmin.author')}</th><th>{t('settingsAdmin.pluginStatus')}</th><th>{t('settingsAdmin.action')}</th></tr></thead><tbody>{resource.data.results.map((row) => <tr key={row.key}><td><div className={styles.pluginName}><Link to={`/settings/admin/plugins/${encodeURIComponent(row.key)}`}>{row.human_name}</Link>{row.origin === 'sample' && <Badge variant="secondary">{t('pluginSettings.sample')}</Badge>}{row.origin === 'builtin' && <Badge variant="outline">{t('pluginSettings.builtin')}</Badge>}</div></td><td>{row.description}</td><td>{row.mixins.join(', ')}</td><td>{row.version || '—'}</td><td>{row.author}</td><td><Badge variant={row.error ? 'destructive' : row.active ? 'default' : 'secondary'}>{t(row.error ? 'settingsAdmin.pluginError' : row.active ? 'settingsAdmin.pluginActive' : 'settingsAdmin.pluginInactive')}</Badge>{row.dependencies && row.dependencies.state !== 'none' && <span> · {t(`settingsAdmin.dependencies.${row.dependencies.state}`)}</span>}</td><td>{!row.is_builtin && <Button disabled={pending !== null || (!row.active && !!row.dependencies && !['none', 'satisfied'].includes(row.dependencies.state))} onClick={(event) => { focus.current = event.currentTarget; setError(''); setConfirm(row) }}>{t(row.active ? 'settingsAdmin.deactivatePlugin' : 'settingsAdmin.activatePlugin')}</Button>}</td></tr>)}</tbody></table></div>}
    {confirm && <ConfirmDialog title={t(confirm.active ? 'settingsAdmin.deactivatePlugin' : 'settingsAdmin.activatePlugin')} description={`${t(confirm.active ? 'settingsAdmin.confirmDeactivatePlugin' : 'settingsAdmin.confirmActivatePlugin')} ${confirm.human_name}`} pending={pending !== null} error={error && <Alert tone="danger">{error}</Alert>} onCancel={() => { setConfirm(null); setError('') }} onConfirm={() => void changeState(confirm)} returnFocus={focus} confirmLabel={t(confirm.active ? 'settingsAdmin.deactivatePlugin' : 'settingsAdmin.activatePlugin')} />}
    {!!resource.data?.errors.length && <section className={styles.section}><h2>{t('settingsAdmin.pluginErrors')}</h2><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.stage')}</th><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.message')}</th></tr></thead><tbody>{resource.data.errors.map((row, index) => <tr key={`${row.stage}-${row.name}-${index}`}><td>{row.stage}</td><td>{row.name}</td><td>{row.message}</td></tr>)}</tbody></table></div></section>}
  </section></div>
}

export function AdminPluginDetailPage() {
  const { pluginKey = '' } = useParams()
  const { t, language } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getAdminPlugin(key, signal), [])
  const resource = useEmployeeResource(pluginKey, loader)
  const refreshDependencies = resource.refresh
  const data: PluginDetail | null = resource.data
  const [confirmInstall, setConfirmInstall] = useState(false)
  const [installing, setInstalling] = useState(false)
  const [installError, setInstallError] = useState('')
  const focus = useRef<HTMLElement | null>(null)
  const dependencyState = data?.dependencies?.state
  useEffect(() => {
    if (dependencyState !== 'queued' && dependencyState !== 'running') return
    const timer = window.setInterval(() => { void refreshDependencies() }, 3000)
    return () => window.clearInterval(timer)
  }, [dependencyState, refreshDependencies])
  async function installDependencies() {
    setInstalling(true); setInstallError('')
    try {
      const dependencies = await installAdminPluginDependencies(pluginKey)
      resource.updateData((current) => ({ ...current, dependencies }))
      setConfirmInstall(false)
    } catch (cause) { setInstallError(errorText(cause, t('settings.saveError'))) }
    finally { setInstalling(false) }
  }
  return <div className={styles.content}><Link to="/settings/admin/plugins">← {t('settingsAdmin.plugins')}</Link>
    {resource.loading && <p role="status">{t('common.loading')}</p>}{!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {data && <><section className={styles.section}><h2>{data.human_name}</h2><dl className={styles.facts}>{([
      ['description', data.description], ['author', data.author], ['version', data.version], ['published', data.pub_date ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(new Date(data.pub_date)) : null], ['website', data.website], ['license', data.license], ['mixins', data.mixins.join(', ')],
    ] as const).map(([label, value]) => <div key={label}><dt>{t(`settingsAdmin.${label}`)}</dt><dd>{label === 'website' && value ? <a href={value} target="_blank" rel="noreferrer">{value}</a> : value || '—'}</dd></div>)}</dl></section>
      {data.dependencies && <section className={styles.section}><div className={styles.heading}><h2>{t('settingsAdmin.dependencies')}</h2><Button onClick={() => void resource.refresh()}>{t('common.retry')}</Button></div>
        <p role="status">{t(`settingsAdmin.dependencies.${data.dependencies.state}`)}</p>
        {data.dependencies.state === 'failed' && data.dependencies.operation?.message && <p>{data.dependencies.operation.message}</p>}
        {data.dependencies.restart_required && <Alert tone="warning">{t('settingsAdmin.dependenciesRestartHelp')}</Alert>}
        {data.dependencies.errors.map((error) => <Alert key={error} tone="danger">{error}</Alert>)}
        {data.dependencies.requirements.length > 0 && <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.requiredVersion')}</th><th>{t('settingsAdmin.installedVersion')}</th><th>{t('settingsAdmin.diskVersion')}</th><th>{t('settingsAdmin.pluginStatus')}</th></tr></thead><tbody>{data.dependencies.requirements.map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.required}</td><td>{row.installed_version || '—'}</td><td>{row.on_disk_version || '—'}</td><td>{t(`settingsAdmin.dependencies.${row.state}`)}</td></tr>)}</tbody></table></div>}
        {data.dependencies.can_install && <Button disabled={installing} onClick={(event) => { focus.current = event.currentTarget; setConfirmInstall(true) }}>{t('settingsAdmin.installDependencies')}</Button>}
        {installError && !confirmInstall && <Alert tone="danger">{installError}</Alert>}
      </section>}
      {data.sections.settings && <section className={styles.section}><h2>{t('settingsAdmin.settings')}</h2><SettingList key={pluginKey} settings={data.sections.settings} onChange={(key, value) => updateAdminPluginSetting(pluginKey, key, value)} /></section>}
      {data.sections.tokens && <PluginTokensSection key={`${pluginKey}-plugin`} pluginKey={pluginKey} kind="plugin" />}
      {data.sections.schedule && <section className={styles.section}><h2>{t('settingsAdmin.schedule')}</h2><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.function')}</th><th>{t('settingsAdmin.scheduleType')}</th><th>{t('settingsAdmin.repeat')}</th><th>{t('settingsAdmin.nextRun')}</th><th>{t('settingsAdmin.success')}</th></tr></thead><tbody>{data.sections.schedule.map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.function}</td><td>{row.schedule_type}</td><td>{row.repeat ?? '—'}</td><td>{row.next_run ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.next_run)) : '—'}</td><td>{row.success ? '✓' : '—'}</td></tr>)}</tbody></table></div></section>}
      {data.sections.urls && <section className={styles.section}><h2>{t('settingsAdmin.urls')}</h2><p>{t('settingsAdmin.baseUrl')}: {data.sections.urls.base_url}</p><div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>{t('settingsAdmin.name')}</th><th>{t('settingsAdmin.url')}</th><th>{t('settingsAdmin.action')}</th></tr></thead><tbody>{data.sections.urls.routes.map((row) => <tr key={`${row.name}-${row.url}`}><td>{row.name}</td><td>{row.url}</td><td>{row.href && <a href={row.href} target="_blank" rel="noreferrer">{t('settingsAdmin.openNewTab')}</a>}</td></tr>)}</tbody></table></div></section>}
      {confirmInstall && <ConfirmDialog title={t('settingsAdmin.installDependencies')} description={`${t('settingsAdmin.confirmInstallDependencies')} ${data.dependencies?.requirements.map((row) => `${row.name} ${row.required}`).join(', ')}`} pending={installing} error={installError && <Alert tone="danger">{installError}</Alert>} onCancel={() => { setConfirmInstall(false); setInstallError('') }} onConfirm={() => void installDependencies()} returnFocus={focus} confirmLabel={t('settingsAdmin.installDependencies')} />}
    </>}
  </div>
}
