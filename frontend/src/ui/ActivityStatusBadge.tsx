import { StatusBadge } from './StatusBadge'

export function ActivityStatusBadge({ active }: { active: boolean }) {
  return <StatusBadge tone={active ? 'success' : 'neutral'}>{active ? 'Actif' : 'Inactif'}</StatusBadge>
}
