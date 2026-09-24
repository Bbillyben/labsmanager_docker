import { Moon, Sun } from 'lucide-react'
import { useState } from 'react'
import { DropdownMenuItem } from '../components/ui/dropdown-menu'
import { useTranslation } from '../i18n/i18n'

export function ThemeMenuItem() {
  const { t } = useTranslation()
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const label = dark ? t('user.appearanceLight') : t('user.appearanceDark')

  return <DropdownMenuItem onClick={() => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    setDark(next)
    try { localStorage.setItem('labsmanager-theme', next ? 'dark' : 'light') } catch { /* The theme remains usable without browser storage. */ }
  }}>{dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />} {label}</DropdownMenuItem>
}
