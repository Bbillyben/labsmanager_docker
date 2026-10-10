import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { useAuth } from '../auth/AuthContext'
import { completeInvitationSignup, exchangeInvitation, getInvitationSignup, type InvitationSignup } from '../auth/invitationApi'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { AuthFrame } from './PasswordResetPage'
import styles from './LoginPage.module.css'

type InvitationState = 'invalid' | 'expired' | 'accepted' | 'account_exists' | 'authenticated' | 'network'

function stateFromError(error: unknown): InvitationState {
  if (error instanceof ApiError) {
    const state = (error.payload as { state?: string } | null)?.state
    if (state === 'invalid' || state === 'expired' || state === 'accepted' || state === 'account_exists' || state === 'authenticated') return state
  }
  return 'network'
}

export function InvitationBridgePage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const auth = useAuth()
  const { t } = useTranslation()
  const exchange = useRef<Promise<InvitationSignup> | null>(null)

  useEffect(() => {
    if (auth.status === 'loading' || auth.status === 'error') return
    if (auth.status === 'authenticated') {
      navigate('/invitations/accept/?state=authenticated', { replace: true })
      return
    }
    if (!token) {
      navigate('/invitations/accept/?state=invalid', { replace: true })
      return
    }
    exchange.current ??= exchangeInvitation(token)
    let active = true
    exchange.current.then(() => { if (active) navigate('/invitations/accept/', { replace: true }) })
      .catch((error) => { if (active) navigate(`/invitations/accept/?state=${stateFromError(error)}`, { replace: true }) })
    return () => { active = false }
  }, [auth.status, navigate, token])

  if (auth.status === 'error') return <ErrorState />
  return <main className="centered-state"><LoadingState message={t('common.loading')} /></main>
}

export function InvitationAcceptPage() {
  const auth = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [query] = useSearchParams()
  const forcedState = query.get('state')
  const [invitation, setInvitation] = useState<InvitationSignup | null>(null)
  const [state, setState] = useState<InvitationState | 'loading' | 'valid' | 'complete'>('loading')
  const [username, setUsername] = useState('')
  const [password1, setPassword1] = useState('')
  const [password2, setPassword2] = useState('')
  const mutation = useMutation()
  const errors = mutation.error ? normalizeMutationError(mutation.error) : null
  const displayState = forcedState ? stateFromError(new ApiError(400, { state: forcedState })) : state

  useEffect(() => {
    if (forcedState) return
    if (auth.status !== 'unauthenticated') return
    let active = true
    getInvitationSignup().then((result) => { if (active) { setInvitation(result); setState('valid') } })
      .catch((error) => { if (active) setState(stateFromError(error)) })
    return () => { active = false }
  }, [auth.status, forcedState])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    let failure: unknown
    const result = await mutation.run(async () => {
      try { return await completeInvitationSignup({ username, password1, password2 }) }
      catch (error) { failure = error; throw error }
    })
    if (!result) {
      if (failure instanceof ApiError && (failure.payload as { state?: string } | null)?.state) setState(stateFromError(failure))
      return
    }
    if (result.data.authenticated) {
      await auth.refresh()
      navigate('/', { replace: true })
    } else setState('complete')
  }

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message={t('common.loadSession')} /></main>
  if (auth.status === 'error') return <ErrorState />
  if (auth.status === 'authenticated' && displayState !== 'complete') return <AuthFrame title={t('auth.invitationTitle')}><p role="status">{t('auth.invitationAuthenticated')}</p><Link className={styles.helpLink} to="/">{t('auth.invitationGoHome')}</Link></AuthFrame>

  return <AuthFrame title={t('auth.invitationTitle')}>
    {displayState === 'loading' && <p role="status">{t('common.loading')}</p>}
    {displayState === 'valid' && invitation && <form className={styles.form} onSubmit={(event) => void submit(event)} aria-busy={mutation.pending}>
      <p>{t('auth.invitationDescription')}</p>
      <label htmlFor="invitation-email">{t('auth.email')}</label><input id="invitation-email" type="email" value={invitation.email} readOnly />
      {invitation.fields.username && <><label htmlFor="invitation-username">{t('auth.username')}</label><input id="invitation-username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></>}
      <label htmlFor="invitation-password">{t('auth.newPassword')}</label><input id="invitation-password" type="password" autoComplete="new-password" required value={password1} onChange={(event) => setPassword1(event.target.value)} />
      {invitation.fields.password2 && <><label htmlFor="invitation-password-confirm">{t('auth.confirmPassword')}</label><input id="invitation-password-confirm" type="password" autoComplete="new-password" required value={password2} onChange={(event) => setPassword2(event.target.value)} /></>}
      {invitation.password_hints.length > 0 && <details><summary>{t('auth.passwordRequirements')}</summary><ul>{invitation.password_hints.map((hint) => <li key={hint}>{hint}</li>)}</ul></details>}
      {errors && <p role="alert" className={styles.error}>{[...errors.messages, ...Object.values(errors.fields).flat()].join(' ') || t('auth.invitationUnavailable')}</p>}
      <Button type="submit" disabled={mutation.pending}>{t('auth.invitationCreateAccount')}</Button>
    </form>}
    {displayState === 'complete' && <><p role="status">{t('auth.invitationComplete')}</p><Link className={styles.helpLink} to="/login">{t('auth.signIn')}</Link></>}
    {displayState !== 'loading' && displayState !== 'valid' && displayState !== 'complete' && <><p role="alert">{t(`auth.invitationState.${displayState}`)}</p><Link className={styles.helpLink} to="/login">{t('auth.backToLogin')}</Link></>}
  </AuthFrame>
}
