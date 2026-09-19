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
import styles from './Sidebar.module.css'

type Capability = keyof Capabilities
type HistoricalItem = { label: string; href: string; capability: Capability; icon: LucideIcon }

const historicalItems: HistoricalItem[] = [
  { label: 'Équipes', href: '/staff/team/', capability: 'view_team_list', icon: UsersRound },
  { label: 'Contrats', href: '/expense/', capability: 'view_contract_list', icon: FileSignature },
  { label: 'Projets', href: '/project/', capability: 'view_project_list', icon: FlaskConical },
  { label: 'Organisations', href: '/infos/', capability: 'view_organizations', icon: Building2 },
  { label: 'Calendrier', href: '/calendar/main', capability: 'view_calendar', icon: CalendarDays },
  { label: 'Tableau de bord', href: '/dashboard/', capability: 'view_dashboard', icon: ChartNoAxesCombined },
  { label: 'Recherche de fonds', href: '/fund/finder', capability: 'use_fund_finder', icon: Search },
  { label: 'Import', href: '/import/', capability: 'import_data', icon: Upload },
]

type SidebarProps = { expanded: boolean; interactive: boolean; user: AuthenticatedUser }

export function Sidebar({ expanded, interactive, user }: SidebarProps) {
  const visibleHistoricalItems = historicalItems.filter((item) => user.capabilities[item.capability])

  return (
    <aside aria-hidden={!interactive} className={styles.sidebar} id="primary-navigation" data-expanded={expanded} inert={!interactive}>
      <div className={styles.brand}>
        <img alt="" aria-hidden="true" className={styles.brandMark} src={`${import.meta.env.BASE_URL}labsmanager-logo.png`} />
        <span className={styles.brandName}>LabsManager</span>
      </div>
      <nav className={styles.navigation} aria-label="Navigation principale">
        <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} end to="/" title="Accueil">
          <Home aria-hidden="true" size={19} strokeWidth={1.8} />
          <span className={styles.label}>Accueil</span>
        </NavLink>
        {user.capabilities.view_employee_list && (
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/employees/" title="Employés">
            <Users aria-hidden="true" size={19} strokeWidth={1.8} />
            <span className={styles.label}>Employés</span>
          </NavLink>
        )}
        {visibleHistoricalItems.length > 0 && (
          <div className={styles.group}>
            <p className={styles.groupTitle}>Interface historique</p>
            {visibleHistoricalItems.map((item) => {
              const Icon = item.icon
              return (
              <a className={styles.link} href={getDjangoUrl(item.href)} key={item.href} title={`${item.label} — interface historique`}>
                <Icon aria-hidden="true" size={19} strokeWidth={1.8} />
                <span className={styles.label}>{item.label}</span>
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
