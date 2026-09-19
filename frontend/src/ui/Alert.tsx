import type { PropsWithChildren } from 'react'
import styles from './Alert.module.css'

type AlertProps = PropsWithChildren<{ tone?: 'info' | 'success' | 'warning' | 'danger' }>

export function Alert({ children, tone = 'info' }: AlertProps) {
  return <div className={`${styles.alert} ${styles[tone]}`} role={tone === 'danger' ? 'alert' : 'status'}>{children}</div>
}
