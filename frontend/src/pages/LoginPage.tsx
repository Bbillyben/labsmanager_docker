import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/errors'
import { login } from '../auth/authApi'
import { useAuth } from '../auth/AuthContext'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { getDjangoUrl } from '../config/django'
import { Button } from '../ui/Button'
import styles from './LoginPage.module.css'

type LoginLocationState = { from?: unknown }

function safeReturnPath(value: unknown) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

export function LoginPage() {
  const auth = useAuth()
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

  if (auth.status === 'loading') return <main className="centered-state"><LoadingState message="Chargement de la session…" /></main>
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
        setError('Trop de tentatives de connexion. Réessayez plus tard.')
      } else if (caught instanceof ApiError && caught.status === 400) {
        setError('Identifiant ou mot de passe incorrect.')
      } else {
        setError('La connexion est momentanément indisponible.')
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
          <p className={styles.eyebrow}>Espace de travail</p>
          <h1 id="login-title">Connexion</h1>
          <p>Utilisez votre identifiant ou votre adresse email LabsManager.</p>
        </div>
        {error && <p className={styles.error} role="alert">{error}</p>}
        <form className={styles.form} onSubmit={handleSubmit}>
          <label htmlFor="login-identifier">Identifiant ou email</label>
          <input autoComplete="username" autoFocus id="login-identifier" name="login" onChange={(event) => setIdentifier(event.target.value)} required value={identifier} />
          <label htmlFor="login-password">Mot de passe</label>
          <input autoComplete="current-password" id="login-password" name="password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          <Button disabled={submitting} type="submit" variant="primary">{submitting ? 'Connexion…' : 'Se connecter'}</Button>
        </form>
        <a className={styles.helpLink} href={getDjangoUrl('/accounts/password/reset/')}>Mot de passe oublié ?</a>
      </section>
    </main>
  )
}
