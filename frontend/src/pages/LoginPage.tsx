import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/errors'
import { login } from '../auth/authApi'
import { useAuth } from '../auth/AuthContext'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './LoginPage.module.css'

type LoginLocationState = { from?: unknown }

function safeReturnPath(value: unknown) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

export function LoginPage() {
  const auth = useAuth()
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string>()
  const returnPath = safeReturnPath((location.state as LoginLocationState | null)?.from)

  useEffect(() => {
    if (auth.status === 'authenticated') navigate(returnPath, { replace: true })
  }, [auth.status, navigate, returnPath])

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message={t('common.loadSession')} /></main>
  if (auth.status === 'error') return <ErrorState />
  if (auth.status === 'authenticated') return <Navigate replace to={returnPath} />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(undefined)
    try {
      await login({ login: identifier, password })
      await auth.refresh()
      navigate(returnPath, { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else if (caught instanceof ApiError && caught.status === 400) {
        setError(t('auth.invalidCredentials'))
      } else {
        setError(t('auth.unavailable'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className={styles.page}>
      <section aria-labelledby="login-title" className={styles.card}>
        <img alt="LabsManager" className={styles.logo} src={`${import.meta.env.BASE_URL}labsmanager-logo.png`} />
        <div className={styles.heading}>
          <p className={styles.eyebrow}>{t('auth.workspace')}</p>
          <h1 id="login-title">{t('auth.login')}</h1>
          <p>{t('auth.loginDescription')}</p>
        </div>
        {error && <p className={styles.error} role="alert">{error}</p>}
        <form className={styles.form} onSubmit={handleSubmit}>
          <label htmlFor="login-identifier">{t('auth.identifier')}</label>
          <input autoComplete="username" autoFocus id="login-identifier" name="login" onChange={(event) => setIdentifier(event.target.value)} required value={identifier} />
          <label htmlFor="login-password">{t('auth.password')}</label>
          <input autoComplete="current-password" id="login-password" name="password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          <Button disabled={submitting} type="submit" variant="primary">{t(submitting ? 'auth.signingIn' : 'auth.signIn')}</Button>
        </form>
        <Link className={styles.helpLink} to="/password/reset">{t('auth.forgotPassword')}</Link>
      </section>
    </main>
  )
}
