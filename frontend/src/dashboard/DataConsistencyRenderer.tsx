import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { DATA_CONSISTENCY_CHANGED, getConsistencySummary, type ConsistencySummary } from '../api/dataConsistency'
import { useTranslation } from '../i18n/i18n'

export function DataConsistencyRenderer() {
  const { t } = useTranslation()
  const [summary, setSummary] = useState<ConsistencySummary | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    let controller = new AbortController()
    const load = () => {
      controller.abort()
      const requestController = new AbortController()
      controller = requestController
      getConsistencySummary(requestController.signal).then(
        (result) => { if (active && !requestController.signal.aborted) { setSummary(result); setError(false) } },
        () => { if (active && !requestController.signal.aborted) setError(true) },
      )
    }
    load()
    window.addEventListener(DATA_CONSISTENCY_CHANGED, load)
    return () => { active = false; controller.abort(); window.removeEventListener(DATA_CONSISTENCY_CHANGED, load) }
  }, [])

  if (error) return <p role="alert" className="muted-text">{t('dataConsistency.loadError')}</p>
  if (!summary) return <p className="muted-text">{t('common.loading')}</p>
  return <div className="grid gap-3">
    <p><strong className="text-2xl">{summary.total}</strong> {t('dataConsistency.issuesCount', { count: summary.total })}</p>
    {summary.categories.length > 0 && <ul className="grid gap-1">{summary.categories.map((category) =>
      <li key={category.key} className="flex justify-between gap-3"><span>{category.key === 'contracts' ? t('dataConsistency.contracts') : category.key === 'funds' ? t('dataConsistency.funds') : category.key === 'planning' ? t('dataConsistency.planning') : category.key === 'expenses' ? t('dataConsistency.expenses') : category.key === 'projects' ? t('dataConsistency.projects') : category.key}</span><strong>{category.count}</strong></li>,
    )}</ul>}
    <Link className="text-sm underline" to="/tools/data-consistency">{t('dataConsistency.review')}</Link>
  </div>
}
