import { useTranslation } from '../i18n/i18n'
type LoadingStateProps = { message?: string }

export function LoadingState({ message }: LoadingStateProps) {
  const { t } = useTranslation()
  return <div className="loading-state" role="status"><div><div className="loading-indicator" aria-hidden="true" /><p>{message ?? t('common.loading')}</p></div></div>
}
