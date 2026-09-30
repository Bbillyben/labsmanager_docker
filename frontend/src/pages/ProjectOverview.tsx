import { useTranslation } from '../i18n/i18n'
import { Pencil } from 'lucide-react'
import { useMemo, useState } from 'react'
import { createProjectGenericInfo, deleteProjectGenericInfo, getProjectOverviewOptions, updateProjectGenericInfo, type ProjectOverview as ProjectOverviewData } from '../api/projects'
import { CopyableValue } from '../components/common/CopyableValue'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { GenericInfoSection } from './GenericInfoSection'
import { ProjectInstitutionBlock } from './ProjectInstitutionBlock'
import { ProjectParticipantBlock } from './ProjectParticipantBlock'
import { ProjectSheet } from './ProjectSheet'
import type { EmployeeResource } from './useEmployeeResource'
import styles from './ProjectOverview.module.css'

type Props = { projectId: string; resource: EmployeeResource<ProjectOverviewData> }
const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—'

export function ProjectOverview({ projectId, resource }: Props) {
  const { t, language } = useTranslation()
  const [editing, setEditing] = useState(false)
  const project = resource.data
  const genericApi = useMemo(() => ({
    types: async (signal: AbortSignal) => (await getProjectOverviewOptions(projectId, signal)).generic_info_types,
    create: (value: { type_id: number; value: string }) => createProjectGenericInfo(projectId, value),
    update: (id: number, value: string) => updateProjectGenericInfo(projectId, id, value),
    delete: (id: number) => deleteProjectGenericInfo(projectId, id),
  }), [projectId])
  if (!project) return null

  return <section aria-labelledby="project-overview-heading" className={styles.overview}>
    <h2 id="project-overview-heading" className={styles.title}>{t('project.overviewHeading')}</h2>
    {!!resource.refreshError && <Alert tone="warning">{t('project.refreshFailed')} <Button variant="ghost" onClick={() => void resource.refresh()}>{t('project.retryRead')}</Button></Alert>}
    <div className={styles.grid}>
      <div className={styles.column}>
      <section className={styles.section} aria-labelledby="project-information-heading">
        <div className={styles.sectionHeading}><h3 id="project-information-heading">{t('project.information')}</h3>{project.capabilities.can_change && <Button size="xs" variant="secondary" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />{t('common.edit')}</Button>}</div>
        <dl className={styles.details}>
          <div><dt>{t('project.name')}</dt><dd><CopyableValue value={project.name} /></dd></div>
          <div><dt>{t('project.startDate')}</dt><dd>{dateLabel(project.start_date, language)}</dd></div>
          <div><dt>{t('project.endDate')}</dt><dd>{dateLabel(project.end_date, language)}</dd></div>
          <div><dt>{t('project.status')}</dt><dd>{t(project.status ? 'common.active' : 'common.inactive')}</dd></div>
        </dl>
      </section>
      <section className={`${styles.section} ${styles.stacked}`} aria-labelledby="project-generic-heading"><h3 id="project-generic-heading">{t('project.genericInfo')}</h3>
        <GenericInfoSection api={genericApi} data={project.generic_info} refresh={resource.refresh} update={(change) => resource.updateData((previous) => ({ ...previous, generic_info: change(previous.generic_info) }))} />
      </section>
      </div>
      <ProjectInstitutionBlock projectId={projectId} resource={resource} />
      <ProjectParticipantBlock projectId={projectId} resource={resource} />
    </div>
    {editing && <ProjectSheet project={project} onClose={() => setEditing(false)} onSaved={(_id, _created, saved) => {
      resource.updateData((previous) => ({ ...previous, ...saved }))
      setEditing(false)
      void resource.refresh()
    }} />}
  </section>
}
