import { Alert } from '../ui/Alert'

export function ErrorState() {
  return <main className="centered-state"><h1>Application indisponible</h1><Alert tone="danger">La session n’a pas pu être vérifiée. Réessayez ultérieurement.</Alert></main>
}
