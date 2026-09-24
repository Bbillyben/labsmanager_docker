import { useEffect, useMemo, useState } from 'react'
import { getEmployeeContributionWorkload, type ContributionWorkload } from '../api/employees'
import { WorkloadTimeline, type WorkloadPreset } from '../components/WorkloadTimeline'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './EmployeeFunding.module.css'
import { workloadWindow } from './projectWorkloadWindow'

type State = { key: string; data: ContributionWorkload | null; error: unknown }

export function EmployeeContributionWorkload({ employeeId }: { employeeId: string }) {
  const { t } = useTranslation()
  const [preset, setPreset] = useState<WorkloadPreset>('year')
  const [offset, setOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const today = useMemo(() => currentCalendarDate(new Date()), [])
  const range = useMemo(
    () => preset === 'all' ? 'all' as const : workloadWindow(today, preset, offset),
    [offset, preset, today],
  )
  const key = `${employeeId}:${preset}:${offset}:${attempt}`
  const [state, setState] = useState<State>({ key, data: null, error: null })

  useEffect(() => {
    const controller = new AbortController()
    getEmployeeContributionWorkload(employeeId, range, controller.signal).then(
      (data) => { if (!controller.signal.aborted) setState({ key, data, error: null }) },
      (error: unknown) => { if (!controller.signal.aborted) setState({ key, data: null, error }) },
    )
    return () => controller.abort()
  }, [employeeId, key, range])

  const current = state.key === key ? state : { data: null, error: null }
  return <section aria-labelledby="employee-contribution-workload-heading" className={styles.workload}>
    <h3 id="employee-contribution-workload-heading">{t('funding.workloadTitle')}</h3>
    {!current.data && !current.error && <p className={styles.state} role="status">…</p>}
    {Boolean(current.error) && <div className={styles.error} role="alert"><span>{t('funding.workloadError')}</span><Button onClick={() => setAttempt((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {current.data && <WorkloadTimeline
      copy={{
        chart: t('funding.workloadChart'),
        chartDescription: t('funding.workloadDescription'),
        closeDetail: t('workload.closeDetail'),
        emptyWindow: t('funding.workloadEmpty'),
        overload: (value) => t('funding.workloadOverload', { value }),
        total: (value) => t('funding.workloadTotal', { value }),
      }}
      data={{
        range: current.data.range,
        segments: current.data.segments.map((segment) => ({
          ...segment,
          items: segment.contributions.map((contribution) => ({
            id: contribution.id,
            label: contribution.fund.display_name,
            detail: [contribution.project.name, contribution.cost_type?.short_name].filter(Boolean).join(' · '),
            quotity: contribution.quotity,
          })),
        })),
      }}
      onNext={() => setOffset((value) => value + 1)}
      onPresetChange={(value) => { setPreset(value); setOffset(0) }}
      onPrevious={() => setOffset((value) => value - 1)}
      onToday={() => setOffset(0)}
      preset={preset}
      shifted={offset !== 0}
    />}
  </section>
}

function currentCalendarDate(value: Date) { return new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate())) }
