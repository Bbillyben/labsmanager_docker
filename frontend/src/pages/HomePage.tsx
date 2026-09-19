import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../ui/PageHeader'
import { StatusBadge } from '../ui/StatusBadge'

export function HomePage() {
  const auth = useAuth()
  if (auth.status !== 'authenticated') return null
  const displayName = [auth.user.first_name, auth.user.last_name].filter(Boolean).join(' ') || auth.user.username

  return <><PageHeader title={`Bienvenue, ${displayName}`} description="Le nouveau LabsManager se construit progressivement autour de vos données et de vos workflows." meta={<StatusBadge tone="success">Session active</StatusBadge>} /><section className="surface-section" aria-labelledby="workspace-heading"><h2 id="workspace-heading">Espace React</h2><p>Ce shell pose la navigation, l’accessibilité et les fondations visuelles des prochains écrans.</p><p className="muted-text">Les fonctionnalités non encore migrées restent accessibles depuis les liens vers l’interface historique.</p></section></>
}
