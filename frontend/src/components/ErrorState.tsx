import { Alert } from '../ui/Alert'
import { useTranslation } from '../i18n/i18n'

export function ErrorState() {
  const { t } = useTranslation()
  return <main className="centered-state"><h1>{t('common.applicationUnavailable')}</h1><Alert tone="danger">{t('common.sessionCheckFailed')}</Alert></main>
}
