import { useEffect, useState } from 'react'
import { ArrowRight, Copy, LayoutDashboard } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listDashboards, type DashboardSummary } from '../api/dashboards'
import { listRecentItems, type RecentItem } from '../api/recentItems'
import { getSystemInfo, type SystemInfo } from '../api/systemInfo'
import { formatSystemValue } from '../api/systemInfo'
import { useAuth } from '../auth/AuthContext'
import { writeToClipboard } from '../utils/clipboard'
import { genericInfoIcon } from './genericInfoIcons'
import { useTranslation, type TranslationKey } from '../i18n/i18n'
import { PageHeader } from '../ui/PageHeader'
import { Button } from '../ui/Button'
import styles from './HomePage.module.css'

const recentTypeKeys: Record<string, TranslationKey> = {
  project: 'navigation.projects', employee: 'page.employees', fund: 'projectFunding.funds',
  budget: 'projectBudgets.budgets', contract: 'navigation.contracts', team: 'navigation.teams',
  institution: 'organization.institutions', funder: 'organization.funders', calendar: 'calendars.title',
  'fund-explorer': 'financial.fundItems', 'budget-explorer': 'financial.budgets', expenses: 'financial.expenses',
}

const databaseNames: Record<string, string> = {
  postgresql: 'PostgreSQL', sqlite: 'SQLite', mysql: 'MySQL', oracle: 'Oracle', other: 'Other',
}

export function HomePage() {
  const auth = useAuth()
  const { t } = useTranslation()
  const [dashboards, setDashboards] = useState<DashboardSummary[] | null>(null)
  const [recents, setRecents] = useState<RecentItem[] | null>(null)
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [copyResult, setCopyResult] = useState<'copied' | 'failed' | null>(null)

  useEffect(() => {
    if (auth.status !== 'authenticated') return
    const controller = new AbortController()
    void listDashboards().then((items) => { if (!controller.signal.aborted) setDashboards(items) }, () => { if (!controller.signal.aborted) setDashboards([]) })
    void listRecentItems(controller.signal).then((items) => { if (!controller.signal.aborted) setRecents(items) }, () => { if (!controller.signal.aborted) setRecents([]) })
    void getSystemInfo(controller.signal).then((info) => { if (!controller.signal.aborted) setSystemInfo(info) }, () => { if (!controller.signal.aborted) setSystemInfo(null) })
    return () => controller.abort()
  }, [auth.status])

  if (auth.status !== 'authenticated') return null
  async function copySystemInfo() {
    if (auth.status !== 'authenticated') return
    // const database = [systemInfo?.database.vendor && (databaseNames[systemInfo.database.vendor] ?? systemInfo.database.vendor), systemInfo?.database.version].filter(Boolean).join(' ')
    const systemDetails = systemInfo
      ? Object.entries(systemInfo.system_info)
          .filter(([, value]) => value !== null && value !== undefined && value !== '')
          .map(([key, value]) => `${key}: ${formatSystemValue(key, value)}`)
      : []
    const details = [
        'LabsManager system information',
        ...systemDetails,
        `URL: ${window.location.href}`,
        `Browser: ${navigator.userAgent}`,
        `Language: ${navigator.language}`,
        `Theme: ${auth.user.theme}`,
        `Timestamp: ${new Date().toISOString()}`,
      ].join('\n')
    setCopyResult(await writeToClipboard(details) ? 'copied' : 'failed')
  }
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
    <section className={styles.section} aria-labelledby="home-help"><h2 id="home-help">{t('home.helpSupport')}</h2>
      {systemInfo && systemInfo.help_links.length > 0 && <div className={styles.inlineLinks}>{systemInfo.help_links.map((link) => <a href={link.url} key={`${link.label}:${link.url}`} rel="noopener noreferrer" target="_blank">{link.label}</a>)}</div>}
      
       {typeof systemInfo?.system_info.labsmanager_version === 'string' && (
        <p className={styles.version}>
          {t('home.version', {
            version: systemInfo.system_info.labsmanager_version,
          })}
        </p>
      )}
      
      <Button className={styles.copyButton} onClick={() => void copySystemInfo()} size="sm" variant="outline"><Copy aria-hidden="true" size={16} />{t('home.copySystemInfo')}</Button>
      {copyResult && <p aria-live="polite" className={styles.copyResult}>{t(copyResult === 'copied' ? 'home.systemInfoCopied' : 'home.systemInfoCopyFailed')}</p>}
    </section>
  </main>
}
