import { StatusBadge } from './StatusBadge'
import { useTranslation } from '../i18n/i18n'

export function ActivityStatusBadge({ active }: { active: boolean }) {
  const { t } = useTranslation()
  return <StatusBadge tone={active ? 'success' : 'neutral'}>{t(active ? 'common.active' : 'common.inactive')}</StatusBadge>
}
