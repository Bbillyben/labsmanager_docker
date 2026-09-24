import { useTranslation, type TranslationKey } from '../i18n/i18n'
import styles from './EmployeeDetailPage.module.css'

export function EmployeeFuturePanel({ title }: { title: TranslationKey }) {
  const { t } = useTranslation()
  return <section aria-label={t(title)} className={styles.placeholder}>
    <p>{t('employee.panelComingSoon')}</p>
  </section>
}
