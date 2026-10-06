import { Moon, Sun } from 'lucide-react'
import { DropdownMenuItem } from '../components/ui/dropdown-menu'
import { useTranslation } from '../i18n/i18n'
import { useAuth } from '../auth/AuthContext'

export function ThemeMenuItem() {
  const { t } = useTranslation()
  const auth = useAuth()
  if (auth.status !== 'authenticated') return null
  const dark = auth.user.theme === 'dark'
  const label = dark ? t('user.appearanceLight') : t('user.appearanceDark')

  return <DropdownMenuItem onClick={() => { void auth.changeTheme(dark ? 'light' : 'dark').catch(() => {}) }}>
    {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />} {label}
  </DropdownMenuItem>
}
