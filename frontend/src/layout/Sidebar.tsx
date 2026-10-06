import {
  Building2,
  CalendarDays,
  ChartNoAxesCombined,
  FileSignature,
  Landmark,
  Wallet,
  Receipt,
  FlaskConical,
  Home,
  Upload,
  Users,
  UsersRound,
  Network,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { AuthenticatedUser } from '../auth/types'
import { useTranslation } from '../i18n/i18n'
import styles from './Sidebar.module.css'
import { FavoritesMenu } from './FavoritesMenu'
import { SidebarGroup } from './SidebarGroup'

type SidebarProps = { expanded: boolean; interactive: boolean; onRequestExpand: () => void; user: AuthenticatedUser }

export function Sidebar({ expanded, interactive, onRequestExpand, user }: SidebarProps) {
  const { t } = useTranslation()

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
        <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/dashboard" title={t('navigation.dashboard')}><ChartNoAxesCombined aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.dashboard')}</span></NavLink>
        {user.capabilities.view_employee_list && (
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/employees/" title={t('page.employees')}>
            <Users aria-hidden="true" size={19} strokeWidth={1.8} />
            <span className={styles.label}>{t('page.employees')}</span>
          </NavLink>
        )}
        {user.capabilities.view_project_list && <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/projects/" title={t('navigation.projects')}><FlaskConical aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.projects')}</span></NavLink>}
        {user.capabilities.view_team_list && <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/teams/" title={t('navigation.teams')}><UsersRound aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.teams')}</span></NavLink>}
        <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/calendars" title={t('calendars.title')}><CalendarDays aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('calendars.title')}</span></NavLink>
        <FavoritesMenu expanded={expanded} onRequestExpand={onRequestExpand} />

        {user.capabilities.view_organizations && (
          <SidebarGroup title={t('navigation.organizations')} defaultOpen={false}>
            <NavLink
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.active : ''}`
              }
              to="/organizations/institutions"
              title={t('organization.institutions')}
            >
              <Building2 aria-hidden="true" size={19} strokeWidth={1.8} />
              <span className={styles.label}>
                {t('organization.institutions')}
              </span>
            </NavLink>

            <NavLink
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.active : ''}`
              }
              to="/organizations/funders"
              title={t('organization.funders')}
            >
              <Building2 aria-hidden="true" size={19} strokeWidth={1.8} />
              <span className={styles.label}>
                {t('organization.funders')}
              </span>
            </NavLink>
          </SidebarGroup>
        )}
        <SidebarGroup title={t('navigation.tools')} defaultOpen={false}>
          {user.capabilities.import_data && <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/import" title={t('navigation.import')}><Upload aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.import')}</span></NavLink>}
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/organization-chart" title={t('organizationChart.title')}><Network aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('organizationChart.title')}</span></NavLink>
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/contracts" title={t('navigation.contracts')}><FileSignature aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('navigation.contracts')}</span></NavLink>
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/fund-items" title={t('financial.fundItems')}><Landmark aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('financial.fundItems')}</span></NavLink>
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/budgets" title={t('financial.budgets')}><Wallet aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('financial.budgets')}</span></NavLink>
          <NavLink className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`} to="/tools/expenses" title={t('financial.expenses')}><Receipt aria-hidden="true" size={19} strokeWidth={1.8} /><span className={styles.label}>{t('financial.expenses')}</span></NavLink>
        </SidebarGroup>



      </nav>
    </aside>
  )
}
