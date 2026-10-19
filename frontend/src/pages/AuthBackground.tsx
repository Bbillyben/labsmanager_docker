import { useState, type ReactNode } from 'react'
import styles from './LoginPage.module.css'

export function AuthBackground({ children }: { children: ReactNode }) {
  const [backgroundNumber] = useState(() => Math.floor(Math.random() * 3) + 1)

  return <main
    className={styles.page}
    style={{
      backgroundImage: `linear-gradient(145deg, rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.5)), url("${import.meta.env.BASE_URL}labsmanager-background_${backgroundNumber}.png")`,
    }}
  >{children}</main>
}
