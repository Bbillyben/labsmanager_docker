import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getDashboard, getDashboardCatalog, type DashboardCatalog, type DashboardDetail } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { buttonVariants } from '../components/ui/button'
import { DashboardGrid } from './DashboardGrid'
import './DashboardPage.css'

export function DashboardPresentation() {
  const { dashboardId = '' } = useParams()
  const { t } = useTranslation()
  const [detail, setDetail] = useState<DashboardDetail | null>(null)
  const [catalog, setCatalog] = useState<DashboardCatalog | null>(null)
  const [error, setError] = useState(false)
  const id = Number(dashboardId)
  useEffect(() => {
    let active = true
    if (!Number.isSafeInteger(id) || id <= 0) return
    getDashboard(id).then(async (nextDetail) => {
      const nextCatalog = await getDashboardCatalog(nextDetail.scope === 'project' ? nextDetail.project_id ?? undefined : undefined)
      if (active) { setDetail(nextDetail); setCatalog(nextCatalog) }
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [id])
  const definitions = useMemo(() => new Map((catalog?.definitions ?? []).map((item) => [item.key, item])), [catalog])
  const back = detail?.scope === 'project' && detail.project_id ? `/projects/${detail.project_id}/dashboard` : Number.isSafeInteger(id) && id > 0 ? `/dashboard?selected=${id}` : '/dashboard'
  return <main className="dashboard-presentation" id="main-content">
    <header className="dashboard-presentation-header"><Link className={buttonVariants({ variant: 'ghost' })} to={back}><ArrowLeft aria-hidden="true" />{t('dashboard.exitPresentation')}</Link>{detail && <h1>{detail.name}</h1>}</header>
    {!Number.isSafeInteger(id) || id <= 0 || error ? <Alert tone="danger">{t('dashboard.loadError')}</Alert> : !detail || !catalog ? <p role="status" aria-busy="true">{t('common.loading')}</p> : detail.widgets.length ? <DashboardGrid widgets={detail.widgets} definitions={definitions} mode="presentation" /> : <p className="muted-text">{t('dashboard.noWidgets')}</p>}
  </main>
}
