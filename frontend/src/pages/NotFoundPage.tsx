import { Link } from 'react-router-dom'
import { PageHeader } from '../ui/PageHeader'
import { useTranslation } from '../i18n/i18n'

/** Show a route-not-found message with a path back into the application. */
export function NotFoundPage() {
  const { t } = useTranslation()
  return <div><PageHeader title={t('common.notFound')} description={t('common.notFoundDescription')} /><Link to="/">{t('common.backHome')}</Link></div>
}
