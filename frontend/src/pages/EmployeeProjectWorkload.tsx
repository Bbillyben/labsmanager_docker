import { useEffect, useMemo, useState } from 'react'
import { getEmployeeProjectWorkload, type ProjectWorkload } from '../api/employees'
import { ProjectWorkloadTimeline, type WorkloadPreset } from '../components/ProjectWorkloadTimeline'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './EmployeeProjectWorkload.module.css'
import { workloadWindow } from './projectWorkloadWindow'

type State = { key: string; data: ProjectWorkload | null; error: unknown }

export function EmployeeProjectWorkload({ employeeId }: { employeeId: string }) {
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
    getEmployeeProjectWorkload(employeeId, range, controller.signal).then(
      (data) => { if (!controller.signal.aborted) setState({ key, data, error: null }) },
      (error: unknown) => { if (!controller.signal.aborted) setState({ key, data: null, error }) },
    )
    return () => controller.abort()
  }, [employeeId, key, range])

  const current = state.key === key ? state : { data: null, error: null }
  return <section aria-labelledby="employee-project-workload-heading" className={styles.section}>
    <h3 id="employee-project-workload-heading">{t('workload.title')}</h3>
    {!current.data && !current.error && <p className={styles.state} role="status">…</p>}
    {Boolean(current.error) && <div className={styles.error} role="alert"><span>{t('workload.error')}</span><Button onClick={() => setAttempt((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></div>}
    {current.data && <ProjectWorkloadTimeline
      data={current.data}
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
