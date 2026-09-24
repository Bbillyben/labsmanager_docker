import { Link, useParams } from 'react-router-dom'
import { PageHeader } from '../ui/PageHeader'

export function ProjectSinglePendingPage() {
  const { projectId } = useParams()
  return <section><PageHeader title={`Projet ${projectId ?? ''}`} /><p>La fiche du projet sera disponible dans la prochaine étape de la migration.</p><Link to="/projects/">Retour à la liste des projets</Link></section>
}
