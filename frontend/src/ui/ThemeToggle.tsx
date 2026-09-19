import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { IconButton } from './IconButton'

export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  return <IconButton label={dark ? 'Activer le thème clair' : 'Activer le thème sombre'} onClick={() => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    setDark(next)
    try { localStorage.setItem('labsmanager-theme', next ? 'dark' : 'light') } catch { /* The theme remains usable without browser storage. */ }
  }}>{dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}</IconButton>
}
