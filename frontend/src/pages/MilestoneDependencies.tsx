import { useEffect, useRef, useState } from 'react'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { createPlanningDependency, deletePlanningDependency, getEditablePlanningProjects, getPlanningDependencies, getProjectPlanningItems, type PlanningDependencies, type PlanningDependency, type PlanningItem, type PlanningProject } from '../api/planning'
import type { EmployeeMilestone } from '../api/employees'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import styles from './MilestoneDependencies.module.css'

export function MilestoneDependencies({ milestone, onChanged }: { milestone: EmployeeMilestone; onChanged?: () => void }) {
  const { t } = useTranslation()
  const [data, setData] = useState<PlanningDependencies | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [reload, setReload] = useState(0)
  const [projectQuery, setProjectQuery] = useState('')
  const [projects, setProjects] = useState<PlanningProject[]>([])
  const [project, setProject] = useState<PlanningProject | null>(null)
  const [itemQuery, setItemQuery] = useState('')
  const [items, setItems] = useState<PlanningItem[]>([])
  const [item, setItem] = useState<PlanningItem | null>(null)
  const [deleting, setDeleting] = useState<PlanningDependency | null>(null)
  const [adding, setAdding] = useState(false)
  const [showAddError, setShowAddError] = useState(false)
  const deleteButton = useRef<HTMLElement | null>(null)
  const create = useMutation()
  const remove = useMutation()

  useEffect(() => {
    const controller = new AbortController()
    getPlanningDependencies(milestone.id, controller.signal).then((result) => {
      if (!controller.signal.aborted) { setData(result); setLoadError(false) }
    }, () => { if (!controller.signal.aborted) setLoadError(true) })
    return () => controller.abort()
  }, [milestone.id, reload])
  useEffect(() => {
    if (!data?.can_add || !adding) return
    const controller = new AbortController()
    getEditablePlanningProjects(projectQuery, milestone.project.id, controller.signal).then((result) => {
      if (!controller.signal.aborted) {
        setProjects(result)
        if (!projectQuery) setProject((current) => current ?? result.find((candidate) => candidate.id === milestone.project.id) ?? null)
      }
    }, () => { if (!controller.signal.aborted) setProjects([]) })
    return () => controller.abort()
  }, [adding, data?.can_add, milestone.project.id, projectQuery])
  useEffect(() => {
    if (!adding || !project) return
    const controller = new AbortController()
    getProjectPlanningItems(project.id, itemQuery, milestone.id, controller.signal).then((result) => {
      if (!controller.signal.aborted) setItems(result)
    }, () => { if (!controller.signal.aborted) setItems([]) })
    return () => controller.abort()
  }, [adding, project, itemQuery, milestone.id, reload])

  async function add() {
    if (!item) return
    const result = await create.run(() => createPlanningDependency(milestone.id, item.id))
    if (result) { setAdding(false); setItem(null); setItemQuery(''); setReload((value) => value + 1); onChanged?.() }
    else setShowAddError(true)
  }
  async function confirmDelete() {
    if (!deleting) return
    const result = await remove.run(() => deletePlanningDependency(milestone.id, deleting.id))
    if (result) { setDeleting(null); setReload((value) => value + 1); onChanged?.() }
  }
  const addError = create.error ? normalizeMutationError(create.error) : null
  const removeError = remove.error ? normalizeMutationError(remove.error) : null
  const errorText = (error: NonNullable<typeof addError>) => {
    const code = error.fields.code?.[0]
    if (code === 'cycle' || code === 'duplicate' || code === 'self_dependency') return t(`planning.${code}`)
    return error.messages.join(' ') || Object.entries(error.fields).filter(([key]) => key !== 'code').flatMap(([, values]) => values).join(' ') || t(`genericInfo.error.${error.kind}`)
  }

  return <section className={styles.root} aria-label={t('planning.dependencies')}>
    <h3>{t('planning.dependencies')}</h3>
    {loadError && <p role="alert">{t('planning.loadError')} <Button onClick={() => setReload((value) => value + 1)} size="xs" variant="ghost">{t('common.retry')}</Button></p>}
    {!data && !loadError && <p role="status">{t('genericInfo.loading')}</p>}
    {data && <>
      {!data.predecessors.length && <p>{t('planning.empty')}</p>}
      <ul className={styles.list}>{data.predecessors.map((dependency) => <li key={dependency.id}>
        <span><strong>{dependency.predecessor.name}</strong> · {dependency.predecessor.project.name} · {t(dependency.predecessor.work_kind === 'task' ? 'employee.task' : 'employee.milestone')}
          {dependency.temporally_inconsistent && <small className={styles.warning}>{t('planning.temporalWarning')}</small>}</span>
        {dependency.can_delete && <Button aria-label={t('planning.deleteAction', { name: dependency.predecessor.name })} onClick={(event) => { deleteButton.current = event.currentTarget; setDeleting(dependency) }} size="xs" variant="ghost">{t('genericInfo.delete')}</Button>}
      </li>)}</ul>
      {data.can_add && !adding && <Button onClick={() => { setShowAddError(false); setAdding(true) }} size="sm" variant="ghost">{t('planning.addPredecessor')}</Button>}
      {data.can_add && adding && <div className={styles.form}>
        <label htmlFor="planning-project-search">{t('planning.project')}</label>
        <input id="planning-project-search" onChange={(event) => { setProjectQuery(event.target.value); setProject(null); setItem(null); setItems([]) }} placeholder={t('planning.searchProject')} value={projectQuery} />
        <select aria-label={t('planning.project')} onChange={(event) => { setProject(projects.find((candidate) => candidate.id === Number(event.target.value)) ?? null); setItem(null); setItemQuery(''); setItems([]) }} value={project?.id ?? ''}>
          <option value="">{t('planning.chooseProject')}</option>
          {projects.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}
        </select>
        {project && <>
          <label htmlFor="planning-item-search">{t('planning.predecessor')}</label>
          <input id="planning-item-search" onChange={(event) => { setItemQuery(event.target.value); setItem(null) }} placeholder={t('planning.searchItem')} value={itemQuery} />
          <select aria-label={t('planning.predecessor')} onChange={(event) => setItem(items.find((candidate) => candidate.id === Number(event.target.value)) ?? null)} value={item?.id ?? ''}>
            <option value="">{t('planning.chooseItem')}</option>
            {items.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name} · {t(candidate.work_kind === 'task' ? 'employee.task' : 'employee.milestone')}</option>)}
          </select>
        </>}
        {showAddError && addError && <p role="alert">{errorText(addError)}</p>}
        <div className={styles.actions}>
          <Button disabled={!item || create.pending} onClick={() => void add()} size="sm">{t('planning.add')}</Button>
          <Button disabled={create.pending} onClick={() => { setAdding(false); setShowAddError(false) }} size="sm" variant="ghost">{t('genericInfo.cancel')}</Button>
        </div>
      </div>}
    </>}
    {deleting && <ConfirmDialog title={t('planning.deleteTitle')} description={t('planning.deleteDescription', { name: deleting.predecessor.name })} pending={remove.pending} onCancel={() => setDeleting(null)} onConfirm={() => void confirmDelete()} returnFocus={deleteButton} error={removeError && <span role="alert">{errorText(removeError)}</span>} />}
  </section>
}
