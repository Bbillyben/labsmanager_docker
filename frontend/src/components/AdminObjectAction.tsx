import { ExternalLink } from 'lucide-react'
import { getDjangoUrl } from '../config/django'
import { useTranslation } from '../i18n/i18n'
import { DropdownMenuItem } from './ui/dropdown-menu'

export function AdminObjectAction({ adminUrl }: { adminUrl?: string | null }) {
  const { t } = useTranslation()
  if (!adminUrl) return null
  return <DropdownMenuItem render={<a href={getDjangoUrl(adminUrl)} target="_blank" rel="noreferrer" />}>
    <ExternalLink aria-hidden="true" />{t('admin.open')}
  </DropdownMenuItem>
}
