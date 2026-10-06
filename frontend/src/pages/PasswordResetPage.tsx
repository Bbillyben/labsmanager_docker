import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, normalizeMutationError } from '../api/errors'
import { confirmPasswordReset, getPasswordReset, requestPasswordReset } from '../auth/authApi'
import { useAuth } from '../auth/AuthContext'
import { exchangePasswordResetToken } from '../auth/resetBridge'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './LoginPage.module.css'

function AuthFrame({ title, children }: { title: string; children: React.ReactNode }) {
  const { t } = useTranslation()
  return <main className={styles.page}><section className={styles.card} aria-labelledby="auth-flow-title">
    <img alt="LabsManager" className={styles.logo} src={`${import.meta.env.BASE_URL}labsmanager-logo.png`} />
    <div className={styles.heading}><p className={styles.eyebrow}>{t('auth.workspace')}</p><h1 id="auth-flow-title">{title}</h1></div>
    {children}
  </section></main>
}

export function PasswordResetBridgePage() {
  const { key = '' } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  useEffect(() => {
    let active = true
    if (key) {
      exchangePasswordResetToken(key)
        .then(({ uid }) => { if (active) navigate(`/password/reset/${uid}/`, { replace: true }) })
        .catch(() => { if (active) navigate('/password/reset/invalid/', { replace: true }) })
    }
    return () => { active = false }
  }, [key, navigate])

  return <main className="centered-state"><LoadingState message={t('common.loading')} /></main>
}

export function PasswordResetRequestPage() {
  const { t } = useTranslation()
  const auth = useAuth()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError('')
    try { await requestPasswordReset(email); setSent(true) }
    catch (caught) { setError(caught instanceof ApiError && caught.status === 429 ? t('auth.tooManyAttempts') : t('auth.resetUnavailable')) }
    finally { setPending(false) }
  }

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message={t('common.loadSession')} /></main>
  if (auth.status === 'error') return <ErrorState />

  return <AuthFrame title={t('auth.resetRequestTitle')}>
    {sent ? <p role="status">{t('auth.resetSent')}</p> : <>
      <p>{t('auth.resetRequestDescription')}</p>
      <form className={styles.form} onSubmit={submit}>
        <label htmlFor="reset-email">{t('auth.email')}</label>
        <input id="reset-email" type="email" autoComplete="email" required autoFocus value={email} onChange={(event) => setEmail(event.target.value)} />
        {error && <p role="alert" className={styles.error}>{error}</p>}
        <Button type="submit" disabled={pending}>{t('auth.sendReset')}</Button>
      </form>
    </>}
    <Link className={styles.helpLink} to="/login">{t('auth.backToLogin')}</Link>
  </AuthFrame>
}

export function PasswordResetConfirmPage() {
  const { t } = useTranslation()
  const auth = useAuth()
  const { uid = '' } = useParams()
  const [status, setStatus] = useState<'loading' | 'valid' | 'invalid' | 'saved'>('loading')
  const [hints, setHints] = useState<string[]>([])
  const [password1, setPassword1] = useState('')
  const [password2, setPassword2] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getPasswordReset(uid).then((result) => { if (active) { setHints(result.password_hints); setStatus('valid') } })
      .catch(() => { if (active) setStatus('invalid') })
    return () => { active = false }
  }, [uid])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError('')
    try { await confirmPasswordReset(uid, password1, password2); setStatus('saved') }
    catch (caught) {
      if (caught instanceof ApiError && caught.status === 400 && (caught.payload as { valid?: boolean })?.valid === false) setStatus('invalid')
      else { const details = normalizeMutationError(caught); setError([...details.messages, ...Object.values(details.fields).flat()].join(' ') || t('auth.resetUnavailable')) }
    } finally { setPending(false) }
  }

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message={t('common.loadSession')} /></main>
  if (auth.status === 'error') return <ErrorState />

  return <AuthFrame title={t('auth.resetConfirmTitle')}>
    {status === 'loading' && <p role="status">{t('common.loading')}</p>}
    {status === 'invalid' && <><p role="alert">{t('auth.resetInvalid')}</p><Link className={styles.helpLink} to="/password/reset">{t('auth.requestNewLink')}</Link></>}
    {status === 'saved' && <><p role="status">{t('auth.resetSaved')}</p><Link className={styles.helpLink} to="/login">{t('auth.signIn')}</Link></>}
    {status === 'valid' && <form className={styles.form} onSubmit={submit}>
      <label htmlFor="reset-password">{t('auth.newPassword')}</label>
      <input id="reset-password" type="password" autoComplete="new-password" required value={password1} onChange={(event) => setPassword1(event.target.value)} />
      <label htmlFor="reset-password-confirm">{t('auth.confirmPassword')}</label>
      <input id="reset-password-confirm" type="password" autoComplete="new-password" required value={password2} onChange={(event) => setPassword2(event.target.value)} />
      {hints.length > 0 && <details><summary>{t('auth.passwordRequirements')}</summary><ul>{hints.map((hint) => <li key={hint}>{hint}</li>)}</ul></details>}
      {error && <p role="alert" className={styles.error}>{error}</p>}
      <Button type="submit" disabled={pending}>{t('auth.setNewPassword')}</Button>
    </form>}
  </AuthFrame>
}
