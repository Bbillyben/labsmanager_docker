import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/errors'
import { useAuth } from '../auth/AuthContext'
import { confirmEmail, exchangeEmailConfirmationKey, getEmailConfirmation, type EmailConfirmation } from '../auth/emailConfirmationApi'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { AuthFrame } from './PasswordResetPage'
import styles from './LoginPage.module.css'

type State = EmailConfirmation['state'] | 'loading' | 'invalid' | 'error'

function stateFromError(error: unknown): State {
  if (error instanceof ApiError && error.status === 400 && (error.payload as { state?: string } | null)?.state === 'invalid') return 'invalid'
  return 'error'
}

export function EmailConfirmationBridgePage() {
  const { key = '' } = useParams()
  const navigate = useNavigate()
  const auth = useAuth()
  const { refresh, markUnauthenticated, status } = auth
  const { t } = useTranslation()
  const exchange = useRef<Promise<EmailConfirmation> | null>(null)

  useEffect(() => {
    if (status === 'loading' || status === 'error') return
    if (!key) { navigate('/email/confirm/?state=invalid', { replace: true }); return }
    exchange.current ??= exchangeEmailConfirmationKey(key)
    let active = true
    exchange.current.then(() => {
      if (!active) return
      navigate('/email/confirm/', { replace: true })
      if (status === 'authenticated') void refresh().catch(markUnauthenticated)
    }).catch((error) => { if (active) navigate(`/email/confirm/?state=${stateFromError(error)}`, { replace: true }) })
    return () => { active = false }
  }, [status, refresh, markUnauthenticated, key, navigate])

  if (auth.status === 'error') return <ErrorState />
  return <main className="centered-state"><LoadingState message={t('common.loading')} /></main>
}

export function EmailConfirmationPage() {
  const { t } = useTranslation()
  const auth = useAuth()
  const [query] = useSearchParams()
  const forcedState = query.get('state')
  const [state, setState] = useState<State>('loading')
  const [email, setEmail] = useState('')
  const [pending, setPending] = useState(false)
  const displayState = forcedState === 'invalid' || forcedState === 'error' ? forcedState : state

  useEffect(() => {
    if (forcedState || auth.status === 'loading' || auth.status === 'error') return
    let active = true
    getEmailConfirmation().then((result) => {
      if (active) { setState(result.state); setEmail(result.email ?? '') }
    }).catch((error) => { if (active) setState(stateFromError(error)) })
    return () => { active = false }
  }, [auth.status, forcedState])

  async function submit() {
    setPending(true)
    try {
      const result = await confirmEmail()
      setState(result.state)
      if (auth.status === 'authenticated') void auth.refresh().catch(() => { })
    } catch (error) { setState(stateFromError(error)) }
    finally { setPending(false) }
  }

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message={t('common.loadSession')} /></main>
  if (auth.status === 'error') return <ErrorState />
  return <AuthFrame title={t('auth.emailConfirmTitle')} description={displayState === 'confirmation_required' ? `${t('auth.emailConfirmPrompt')}${email ? ` ${email}` : ''}` : undefined}>
    {displayState === 'loading' && <p role="status">{t('common.loading')}</p>}
    {displayState === 'confirmation_required' && <>
      <Button type="button" disabled={pending} onClick={() => void submit()}>{pending ? t('common.loading') : t('auth.emailConfirmAction')}</Button>
    </>}
    {displayState === 'confirmed' && <p role="status">{t('auth.emailConfirmed')}</p>}
    {displayState === 'already_confirmed' && <p role="status">{t('auth.emailAlreadyConfirmed')}</p>}
    {displayState === 'invalid' && <p role="alert">{t('auth.emailConfirmInvalid')}</p>}
    {displayState === 'error' && <p role="alert" className={styles.error}>{t('auth.emailConfirmError')}</p>}
    {displayState !== 'loading' && <Link className={styles.helpLink} to={auth.status === 'authenticated' && displayState === 'invalid' ? '/settings/user' : auth.status === 'authenticated' ? '/' : '/login'}>{auth.status === 'authenticated' && displayState === 'invalid' ? t('auth.emailManageAddress') : auth.status === 'authenticated' ? t('auth.invitationGoHome') : t('auth.signIn')}</Link>}
  </AuthFrame>
}
