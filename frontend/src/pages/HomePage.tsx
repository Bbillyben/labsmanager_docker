import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../ui/PageHeader'
import { StatusBadge } from '../ui/StatusBadge'
import { useTranslation } from '../i18n/i18n'

export function HomePage() {
  const auth = useAuth()
  const { t } = useTranslation()
  if (auth.status !== 'authenticated') return null
  const displayName = [auth.user.first_name, auth.user.last_name].filter(Boolean).join(' ') || auth.user.username

  return <><PageHeader title={t('home.welcome', { name: displayName })} description={t('home.description')} meta={<StatusBadge tone="success">{t('home.activeSession')}</StatusBadge>} /><section className="surface-section" aria-labelledby="workspace-heading"><h2 id="workspace-heading">{t('home.reactWorkspace')}</h2><p>{t('home.shellDescription')}</p><p className="muted-text">{t('home.legacyDescription')}</p></section></>
}
