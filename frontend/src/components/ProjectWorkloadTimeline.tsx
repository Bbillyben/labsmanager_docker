import type { ProjectWorkload } from '../api/employees'
import { useTranslation } from '../i18n/i18n'
import { WorkloadTimeline, type WorkloadPreset } from './WorkloadTimeline'

export type { WorkloadPreset } from './WorkloadTimeline'

type Props = {
  data: ProjectWorkload
  preset: WorkloadPreset
  shifted: boolean
  onPresetChange: (preset: WorkloadPreset) => void
  onPrevious: () => void
  onNext: () => void
  onToday: () => void
}

export function ProjectWorkloadTimeline(props: Props) {
  const { t } = useTranslation()
  return <WorkloadTimeline
    {...props}
    copy={{
      chart: t('workload.chart'),
      chartDescription: t('workload.chartDescription'),
      closeDetail: t('workload.closeDetail'),
      emptyWindow: t('workload.emptyWindow'),
      overload: (value) => t('workload.overload', { value }),
      total: (value) => t('workload.total', { value }),
    }}
    data={{
      range: props.data.range,
      segments: props.data.segments.map((segment) => ({
        ...segment,
        items: segment.projects.map((project) => ({
          id: project.id,
          label: project.name,
          quotity: project.quotity,
        })),
      })),
    }}
  />
}
