import { useEffect, useState } from 'react'
import { ArrowRight, LayoutDashboard } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listDashboards, type DashboardSummary } from '../api/dashboards'
import { listRecentItems, type RecentItem } from '../api/recentItems'
import { useAuth } from '../auth/AuthContext'
import { genericInfoIcon } from './genericInfoIcons'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { PageHeader } from '../ui/PageHeader'
import styles from './HomePage.module.css'

const recentTypeKeys: Record<string, TranslationKey> = {
  project: 'navigation.projects', employee: 'page.employees', fund: 'projectFunding.funds',
  budget: 'projectBudgets.budgets', contract: 'navigation.contracts', team: 'navigation.teams',
  institution: 'organization.institutions', funder: 'organization.funders', calendar: 'calendars.title',
  'fund-explorer': 'financial.fundItems', 'budget-explorer': 'financial.budgets', expenses: 'financial.expenses',
}

export function HomePage() {
  const auth = useAuth()
  const { t } = useTranslation()
  const [dashboards, setDashboards] = useState<DashboardSummary[] | null>(null)
  const [recents, setRecents] = useState<RecentItem[] | null>(null)

  useEffect(() => {
    if (auth.status !== 'authenticated') return
    const controller = new AbortController()
    void listDashboards().then((items) => { if (!controller.signal.aborted) setDashboards(items) }, () => { if (!controller.signal.aborted) setDashboards([]) })
    void listRecentItems(controller.signal).then((items) => { if (!controller.signal.aborted) setRecents(items) }, () => { if (!controller.signal.aborted) setRecents([]) })
    return () => controller.abort()
  }, [auth.status])

  if (auth.status !== 'authenticated') return null
  const displayName = auth.user.employee ? auth.user.employee.first_name : [auth.user.first_name, auth.user.last_name].filter(Boolean).join(' ') || auth.user.username
  const primary = dashboards?.find((item) => item.is_default) ?? dashboards?.[0]
  const others = dashboards?.filter((item) => item.id !== primary?.id) ?? []
  const quick: { key: TranslationKey; url: string }[] = []
  if (auth.user.capabilities.view_calendar) quick.push({ key: 'calendars.title', url: '/calendars' })
  if (auth.user.capabilities.view_project_list) quick.push({ key: 'navigation.projects', url: '/projects/' })
  if (auth.user.capabilities.view_employee_list) quick.push({ key: 'page.employees', url: '/employees/' })
  if (auth.user.capabilities.view_team_list) quick.push({ key: 'navigation.teams', url: '/teams/' })
  quick.push({ key: 'financial.fundItems', url: '/tools/fund-items' })

  return <main className={styles.home}>
    <PageHeader title={t('home.welcome', { name: displayName })} />
    <section className={styles.section} aria-labelledby="home-dashboards"><h2 id="home-dashboards">{t('home.dashboards')}</h2>
      {dashboards && (primary ? <>
        <Link className={styles.primary} to={`/dashboard?selected=${primary.id}`}>
          <LayoutDashboard aria-hidden="true" />
          <span><strong>{primary.name}</strong><small>{t('home.defaultDashboard')}</small></span><ArrowRight aria-hidden="true" />
        </Link>
        {others.length > 0 && <div className={styles.inlineLinks}>{others.map((item) => <Link key={item.id} to={`/dashboard?selected=${item.id}`}>{item.name}</Link>)}</div>}</>
        : <Link className={styles.primary} to="/dashboard">
          <LayoutDashboard aria-hidden="true" /><span>{t('home.createDashboard')}</span><ArrowRight aria-hidden="true" /></Link>)}
    </section>
    <section className={styles.section} aria-labelledby="home-recents"><h2 id="home-recents">{t('home.resume')}</h2>
      {recents && (recents.length ? <ul className={styles.recents}>{recents.map((item) => {
        const Icon = genericInfoIcon(item.icon)
        const title = item.obj_id === null ? t(recentTypeKeys[item.url_id] ?? 'page.home') : item.title
        return <li key={`${item.url_id}:${item.obj_id ?? ''}`}><Link to={item.url.startsWith('/app/') ? item.url.slice(4) : item.url}><Icon aria-hidden="true" size={19} /><span>{item.obj_id !== null && <small>{t(recentTypeKeys[item.url_id] ?? 'page.home')}</small>}<strong>{title}</strong>{item.subtitle && <small>{item.subtitle}</small>}</span><ArrowRight aria-hidden="true" size={16} /></Link></li>
      })}</ul> : <p className={styles.empty}>{t('home.noRecents')}</p>)}
    </section>
    {quick.length > 0 && <section className={styles.section} aria-labelledby="home-quick"><h2 id="home-quick">{t('home.quickAccess')}</h2><div className={styles.inlineLinks}>{quick.map((item) => <Link key={item.url} to={item.url}>{t(item.key)}</Link>)}</div></section>}
  </main>
}
