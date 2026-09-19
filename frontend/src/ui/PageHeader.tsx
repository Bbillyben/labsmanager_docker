import type { ReactNode } from 'react'
import styles from './PageHeader.module.css'

type PageHeaderProps = { title: string; description?: string; meta?: ReactNode; actions?: ReactNode }

export function PageHeader({ title, description, meta, actions }: PageHeaderProps) {
  return <header className={styles.header}><div className={styles.copy}><h1 className={styles.title}>{title}</h1>{description && <p className={styles.description}>{description}</p>}{meta && <div className={styles.meta}>{meta}</div>}</div>{actions && <div className={styles.actions}>{actions}</div>}</header>
}
