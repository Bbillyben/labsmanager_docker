import { Check, Send, Trash2 } from 'lucide-react'
import { useCallback, useRef, useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { getFavorites, getSubscriptions, setObjectPreference, type FavoriteItem, type PreferenceType } from '../api/preferences'
import { normalizeMutationError } from '../api/errors'
import { addUserEmail, changeUserPassword, getUserAccount, getUserSettings, removeUserEmail, updateUserEmail, updateUserSetting, type EmailAddress, type UserSettingData, type UserSettingSection } from '../api/userSettings'
import type { SettingValue } from '../api/settings'
import { useAuth } from '../auth/AuthContext'
import { Input } from '../components/ui/input'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { EntityActionMenu, type EntityAction } from '../components/EntityActionMenu'
import { Badge } from '../components/ui/badge'
import { getDjangoUrl } from '../config/django'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useEmployeeResource } from './useEmployeeResource'
import { getMutableLists } from '../api/mutableLists'
import styles from './SettingsHubPage.module.css'

function errorText(error: unknown, fallback: string) {
  const normalized = normalizeMutationError(error)
  return [...normalized.messages, ...Object.values(normalized.fields).flat()].join(' ') || fallback
}

const sections = ['user', 'interface', 'notifications', 'common', 'stale'] as const

export function SettingsHubPage() {
  const { t } = useTranslation()
  const auth = useAuth()
  const loader = useCallback((_key: string, signal: AbortSignal) => getMutableLists(signal), [])
  const lists = useEmployeeResource('mutable-lists', loader)
  return <div className="grid gap-5">
    <PageHeader title={t('userSettings.title')} />
    <div className={styles.layout}>
      <nav aria-label={t('userSettings.navigation')} className={styles.navigation}>
        {sections.map((section) => <NavLink key={section} to={`/settings/${section}`}>{t(`userSettings.${section}`)}</NavLink>)}
        {lists.data && lists.data.groups.length > 0 && <><span className={styles.navHeading}>{t('mutableLists.group')}</span>
          {lists.data.groups.map((group) => <NavLink key={group.key} to={`/settings/lists/${group.key}`}>{group.label}</NavLink>)}
        </>}
        {auth.status === 'authenticated' && auth.user.is_staff && <><span className={styles.navHeading}>{t('settingsAdmin.administration')}</span>
          {(['general', 'users', 'notifications', 'plugins'] as const).map((section) => <NavLink key={section} to={`/settings/admin/${section}`}>{t(`settingsAdmin.${section}`)}</NavLink>)}
        </>}
      </nav>
      <div className={styles.content}>
        {!!lists.error && <Alert tone="danger">{t('mutableLists.registryError')} <Button variant="ghost" onClick={lists.retry}>{t('common.retry')}</Button></Alert>}
        <Outlet context={lists.error ? [] : lists.data?.groups ?? null} />
      </div>
    </div>
  </div>
}

export function UserSettingsSection({ section }: { section: UserSettingSection }) {
  const { t } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getUserSettings(key as UserSettingSection, signal), [])
  const resource = useEmployeeResource(section, loader)
  const [pending, setPending] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<string | null>(null)

  async function save(key: string, value: SettingValue): Promise<UserSettingData | null> {
    if (pending) return null
    setPending(key)
    setSaved(null)
    setErrors((current) => ({ ...current, [key]: '' }))
    try {
      const result = await updateUserSetting(section, key, value)
      resource.updateData((current) => ({ settings: current.settings.map((item) => item.key === key ? result : item) }))
      setSaved(key)
      return result
    } catch (error) {
      setErrors((current) => ({ ...current, [key]: errorText(error, t('settings.saveError')) }))
      return null
    } finally { setPending(null) }
  }

  return <section aria-label={t(`userSettings.${section}`)} className={styles.section}>
    <h2 className="text-lg font-semibold">{t(`userSettings.${section}`)}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
    {resource.data?.settings.map((setting) => <SettingRow key={setting.key} setting={setting} disabled={pending !== null} saving={pending === setting.key} error={errors[setting.key]} saved={saved === setting.key} onSave={(value) => save(setting.key, value)} />)}
  </section>
}

export function SettingRow({ setting, disabled, saving, error, saved, onSave }: { setting: UserSettingData; disabled: boolean; saving: boolean; error?: string; saved: boolean; onSave: (value: SettingValue) => Promise<UserSettingData | null> }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState(String(setting.value))
  const editable = ['integer', 'decimal', 'string', 'color'].includes(setting.type)
  const readOnly = disabled || !setting.can_change
  async function saveDraft() {
    if (readOnly || draft === String(setting.value)) return
    if (setting.type === 'integer' && !/^-?\d+$/.test(draft)) { setDraft(String(setting.value)); return }
    if (setting.type === 'decimal' && !Number.isFinite(Number(draft))) { setDraft(String(setting.value)); return }
    const result = await onSave(setting.type === 'integer' || setting.type === 'decimal' ? Number(draft) : draft)
    if (result) setDraft(String(result.value))
  }
  return <div className={styles.row}>
    <div><label htmlFor={`user-setting-${setting.key}`} className="font-medium">{setting.name}</label><p className={styles.description}>{setting.description}</p></div>
    <div className={styles.actions}>
      {setting.type === 'boolean' && <input id={`user-setting-${setting.key}`} type="checkbox" role="switch" checked={setting.value === true} disabled={readOnly} onChange={(event) => void onSave(event.target.checked)} />}
      {setting.type === 'choice' && <select id={`user-setting-${setting.key}`} className="h-9 rounded-md border border-input bg-background px-3" value={String(setting.value)} disabled={readOnly} onChange={(event) => void onSave(event.target.value)}>{setting.choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</select>}
      {editable && <><Input id={`user-setting-${setting.key}`} type={setting.type === 'integer' || setting.type === 'decimal' ? 'number' : setting.type === 'color' ? 'color' : 'text'} value={draft} disabled={readOnly} onChange={(event) => setDraft(event.target.value)} onBlur={() => void saveDraft()} onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur() }} />{setting.units && <span className={styles.description}>{setting.units}</span>}</>}
      {saving && <span role="status" className={styles.feedback}>{t('settings.saving')}</span>}
      {saved && <span role="status" className={styles.feedback}>{t('userSettings.saved')}</span>}
      {error && <span role="alert" className={styles.error}>{error}</span>}
    </div>
  </div>
}

export function UserAccountSection() {
  const { t, language } = useTranslation()
  const navigate = useNavigate()
  const auth = useAuth()
  const loader = useCallback((_key: string, signal: AbortSignal) => getUserAccount(signal), [])
  const resource = useEmployeeResource('account', loader)
  const [email, setEmail] = useState('')
  const [oldpassword, setOldpassword] = useState('')
  const [password1, setPassword1] = useState('')
  const [password2, setPassword2] = useState('')
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [passwordPending, setPasswordPending] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordMessage, setPasswordMessage] = useState('')
  const [emailPending, setEmailPending] = useState(false)
  const [emailError, setEmailError] = useState('')
  const [emailMessage, setEmailMessage] = useState('')
  const [deleting, setDeleting] = useState<EmailAddress | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const emailSection = useRef<HTMLElement | null>(null)

  async function mutateEmail(run: () => Promise<{ can_add: boolean; emails: EmailAddress[] }>, success: TranslationKey) {
    setEmailPending(true); setEmailError(''); setEmailMessage('')
    try {
      const result = await run()
      resource.updateData((current) => ({ ...current, ...result }))
      setEmail('')
      setEmailMessage(t(success))
      if (deleting) focus.current = emailSection.current
      setDeleting(null)
    } catch (cause) { setEmailError(errorText(cause, t('settings.saveError'))) }
    finally { setEmailPending(false) }
  }

  function closePassword() {
    if (passwordPending) return
    setPasswordOpen(false)
    setOldpassword(''); setPassword1(''); setPassword2('')
    setPasswordError('')
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault()
    setPasswordPending(true); setPasswordError(''); setPasswordMessage('')
    try {
      const result = await changeUserPassword({ ...(resource.data?.has_usable_password ? { oldpassword } : {}), password1, password2 })
      setOldpassword(''); setPassword1(''); setPassword2('')
      setPasswordMessage(t('userSettings.passwordSaved'))
      setPasswordOpen(false)
      if (result.logged_out) { auth.markUnauthenticated(); navigate('/login', { replace: true }) }
      else resource.updateData((current) => ({ ...current, has_usable_password: true }))
    } catch (cause) { setPasswordError(errorText(cause, t('settings.saveError'))) }
    finally { setPasswordPending(false) }
  }

  function emailActions(row: EmailAddress): EntityAction[] {
    const actions: EntityAction[] = []
    if (row.can_make_primary && !row.primary) actions.push({ id: 'primary', label: t('userSettings.makePrimary'), icon: <Check aria-hidden="true" />, disabled: emailPending, onSelect: () => void mutateEmail(() => updateUserEmail(row.id, 'primary'), 'userSettings.primaryUpdated') })
    if (row.can_resend && !row.verified) actions.push({ id: 'resend', label: t('userSettings.resend'), icon: <Send aria-hidden="true" />, disabled: emailPending, onSelect: () => void mutateEmail(() => updateUserEmail(row.id, 'resend'), 'userSettings.verificationRequested') })
    if (row.can_delete && !row.primary) actions.push({ id: 'delete', label: t('common.delete'), icon: <Trash2 aria-hidden="true" />, disabled: emailPending, onSelect: () => setDeleting(row) })
    return actions
  }

  return <section aria-label={t('userSettings.user')} className={styles.content}>
    <h2 className="text-lg font-semibold">{t('userSettings.user')}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
    {resource.data && <>
      <section className={styles.section}>
        <div className={styles.heading}><h3>{t('userSettings.account')}</h3><Button variant="secondary" size="sm" onClick={(event) => { focus.current = event.currentTarget; setPasswordOpen(true) }}>{t(resource.data.has_usable_password ? 'userSettings.changePassword' : 'userSettings.setPassword')}</Button></div>
        <dl className={styles.facts}>
          <div><dt>{t('userSettings.username')}</dt><dd>{resource.data.username}</dd></div>
          <div><dt>{t('userSettings.name')}</dt><dd>{[resource.data.first_name, resource.data.last_name].filter(Boolean).join(' ') || '—'}</dd></div>
          <div><dt>{t('userSettings.lastLogin')}</dt><dd>{resource.data.last_login ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(resource.data.last_login)) : '—'}</dd></div>
          <div><dt>{t('userSettings.employee')}</dt><dd>{resource.data.employee ? <Link to={`/employees/${resource.data.employee.id}`}>{resource.data.employee.name}</Link> : '—'}</dd></div>
        </dl>
        {passwordMessage && <p role="status" className={styles.feedback}>{passwordMessage}</p>}
      </section>
      <section ref={emailSection} tabIndex={-1} className={styles.section}>
        <div className={styles.heading}><h3>{t('userSettings.emails')}</h3></div>
        {resource.data.emails.length === 0 && <p>{t('userSettings.noEmails')}</p>}
        <ul className={styles.emailList}>{resource.data.emails.map((row) => <li className={styles.emailRow} key={row.id}>
          <div className={styles.emailIdentity}><span className="font-medium">{row.email}</span><div className={styles.badges}><Badge variant="outline">{t(row.primary ? 'userSettings.primary' : 'userSettings.secondary')}</Badge><Badge variant="secondary">{t(row.verified ? 'userSettings.verified' : 'userSettings.unverified')}</Badge></div></div>
          <EntityActionMenu label={t('common.actionsFor', { name: row.email })} groups={[emailActions(row)]} onTrigger={(trigger) => { focus.current = trigger }} />
        </li>)}</ul>
        {resource.data.can_add && <form className={styles.addEmail} onSubmit={(event) => { event.preventDefault(); void mutateEmail(() => addUserEmail(email), 'userSettings.emailAdded') }}><label>{t('userSettings.addEmail')}<Input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><Button type="submit" disabled={emailPending}>{t('userSettings.addEmail')}</Button></form>}
        {emailMessage && <p role="status" className={styles.feedback}>{emailMessage}</p>}
        {emailError && !deleting && <Alert tone="danger">{emailError}</Alert>}
      </section>
    </>}
    {passwordOpen && resource.data && <Sheet open onOpenChange={(open) => { if (!open) closePassword() }}><SheetContent finalFocus={focus}>
      <SheetHeader><SheetTitle>{t(resource.data.has_usable_password ? 'userSettings.changePassword' : 'userSettings.setPassword')}</SheetTitle><SheetDescription>{t('userSettings.passwordDescription')}</SheetDescription></SheetHeader>
      <form className={styles.form} onSubmit={(event) => void savePassword(event)}>
        {resource.data.has_usable_password && <label>{t('userSettings.currentPassword')}<Input type="password" autoComplete="current-password" required value={oldpassword} onChange={(event) => setOldpassword(event.target.value)} /></label>}
        <label>{t('userSettings.newPassword')}<Input type="password" autoComplete="new-password" required value={password1} onChange={(event) => setPassword1(event.target.value)} /></label>
        <label>{t('userSettings.confirmPassword')}<Input type="password" autoComplete="new-password" required value={password2} onChange={(event) => setPassword2(event.target.value)} /></label>
        {passwordError && <Alert tone="danger">{passwordError}</Alert>}
        <div className={styles.sheetActions}><Button type="button" variant="ghost" disabled={passwordPending} onClick={closePassword}>{t('common.close')}</Button><Button type="submit" disabled={passwordPending}>{t('common.save')}</Button></div>
      </form>
    </SheetContent></Sheet>}
    {deleting && <ConfirmDialog title={t('userSettings.removeEmail')} description={t('userSettings.removeEmailDescription', { email: deleting.email })} pending={emailPending} error={emailError && <Alert tone="danger">{emailError}</Alert>} onCancel={() => { setDeleting(null); setEmailError('') }} onConfirm={() => void mutateEmail(() => removeUserEmail(deleting.id), 'userSettings.emailRemoved')} returnFocus={focus} />}
  </section>
}

export function UserPreferencesSection() {
  const { t } = useTranslation()
  const loader = useCallback((_key: string, signal: AbortSignal) => Promise.all([getFavorites(signal), getSubscriptions(signal)]), [])
  const resource = useEmployeeResource('preferences', loader)
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState('')

  async function remove(kind: 'favorite' | 'subscription', item: FavoriteItem) {
    const key = `${kind}:${item.type}:${item.id}`
    setPending(key); setError('')
    try {
      await setObjectPreference(item.type as PreferenceType, item.id, { [kind]: false })
      resource.updateData((current) => current.map((list, index) => index === (kind === 'favorite' ? 0 : 1) ? list.filter((row) => !(row.type === item.type && row.id === item.id)) : list) as [FavoriteItem[], FavoriteItem[]])
    } catch (cause) { setError(errorText(cause, t('settings.saveError'))) }
    finally { setPending(null) }
  }

  return <section aria-label={t('userSettings.common')} className={styles.content}>
    <h2 className="text-lg font-semibold">{t('userSettings.common')}</h2>
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('settings.loadError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
    {resource.data && <div className={styles.preferenceGrid}>{(['favorite', 'subscription'] as const).map((kind, index) => <section className={styles.section} key={kind}>
      <div className={styles.heading}><h3>{t(kind === 'favorite' ? 'preferences.favorites' : 'userSettings.subscriptions')}</h3></div>
      {!resource.data?.[index].length && <p>{t('userSettings.none')}</p>}
      <ul className={styles.preferenceList}>{resource.data?.[index].map((item) => <li className={styles.preferenceRow} key={`${item.type}:${item.id}`}>
        <div className={styles.preferenceIdentity}><small>{t(`preferences.${item.group}`)}</small>{item.legacy ? <a href={getDjangoUrl(item.url)}>{item.label}</a> : <Link to={item.url}>{item.label}</Link>}</div>
        <Button disabled={pending !== null} onClick={() => void remove(kind, item)} variant="ghost" size="sm">{t('userSettings.remove')}</Button>
      </li>)}</ul>
    </section>)}</div>}
    {error && <Alert tone="danger">{error}</Alert>}
  </section>
}
