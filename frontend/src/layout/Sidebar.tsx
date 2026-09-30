import {
  Building2,
  CalendarDays,
  ChartNoAxesCombined,
  FileSignature,
  FlaskConical,
  Home,
  Search,
  Upload,
  Users,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { AuthenticatedUser, Capabilities } from '../auth/types'
import { getDjangoUrl } from '../config/django'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import styles from './Sidebar.module.css'

type Capability = keyof Capabilities
type HistoricalItem = { label: TranslationKey; href: string; capability: Capability; icon: LucideIcon }

const historicalItems: HistoricalItem[] = [
  { label: 'navigation.teams', href: '/staff/team/', capability: 'view_team_list', icon: UsersRound },
  { label: 'navigation.contracts', href: '/expense/', capability: 'view_contract_list', icon: FileSignature },
  { label: 'navigation.organizations', href: '/infos/', capability: 'view_organizations', icon: Building2 },
  { label: 'navigation.calendar', href: '/calendar/main', capability: 'view_calendar', icon: CalendarDays },
  { label: 'navigation.dashboard', href: '/dashboard/', capability: 'view_dashboard', icon: ChartNoAxesCombined },
  { label: 'navigation.fundFinder', href: '/fund/finder', capability: 'use_fund_finder', icon: Search },
  { label: 'navigation.import', href: '/import/', capability: 'import_data', icon: Upload },
]

type SidebarProps = { expanded: boolean; interactive: boolean; user: AuthenticatedUser }

export function Sidebar({ expanded, interactive, user }: SidebarProps) {
  const { t } = useTranslation()
  const visibleHistoricalItems = historicalItems.filter((item) => user.capabilities[item.capability])

  return (
    <aside aria-hidden={!interactive} className={styles.sidebar} id="primary-navigation" data-expanded={expanded} inert={!interactive}>
      <div className={styles.brand}>
        <img alt="" aria-hidden="true" className={styles.brandMark} src={`${import.meta.env.BASE_URL}labsmanager-logo.png`} />
        <span className={styles.brandName}>LabsManager</span>
      </div>
      <nav className={styles.navigation} aria-label={t('navigation.primary')}>
        <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} end to="/" title={t('page.home')}>
          <Home aria-hidden="true" size={19} strokeWidth={1.8} />
          <span className={styles.label}>{t('page.home')}</span>
        </NavLink>
        {user.capabilities.view_employee_list && (
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/employees/" title={t('page.employees')}>
            <Users aria-hidden="true" size={19} strokeWidth={1.8} />
            <span className={styles.label}>{t('page.employees')}</span>
          </NavLink>
        )}
        {user.capabilities.view_project_list && <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/projects/" title={t('navigation.projects')}><FlaskConical aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.projects')}</span></NavLink>}
        {visibleHistoricalItems.length > 0 && (
          <div className={styles.group}>
            <p className={styles.groupTitle}>{t('navigation.legacy')}</p>
            {visibleHistoricalItems.map((item) => {
              const Icon = item.icon
              return (
              <a className={styles.link} href={getDjangoUrl(item.href)} key={item.href} title={t('navigation.legacyItem', { name: t(item.label) })}>
                <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
                <span className={styles.label}>{t(item.label)}</span>
                <span className={styles.externalMarker} aria-hidden="true">↗</span>
              </a>
              )
            })}
          </div>
        )}
      </nav>
    </aside>
  )
}
