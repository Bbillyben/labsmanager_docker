import styles from './EmptyState.module.css'

type EmptyStateProps = { title: string; description?: string }

export function EmptyState({ title, description }: EmptyStateProps) {
  return <div className={styles.empty}><h2 className={styles.title}>{title}</h2>{description && <p className={styles.description}>{description}</p>}</div>
}
