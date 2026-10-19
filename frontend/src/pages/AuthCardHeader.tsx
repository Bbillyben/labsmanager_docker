import { useTranslation } from '../i18n/i18n'
import styles from './LoginPage.module.css'

export function AuthCardHeader({ title, titleId, description }: { title: string; titleId: string; description?: string }) {
  const { t } = useTranslation()

  return <header className={styles.header}>
    <div className={styles.heading}>
      <p className={styles.eyebrow}>{t('auth.workspace')}</p>
      <h1 id={titleId}>{title}</h1>
      {description && <p className={styles.description}>{description}</p>}
    </div>
    <img alt="LabsManager" className={styles.logo} src={`${import.meta.env.BASE_URL}labsmanager-logo.png`} />
  </header>
}
