import { Link } from 'react-router-dom'
import { PageHeader } from '../ui/PageHeader'

export function NotFoundPage() {
  return <div><PageHeader title="Page introuvable" description="Cette page React n’existe pas ou n’est pas encore disponible." /><Link to="/">Revenir à l’accueil</Link></div>
}
