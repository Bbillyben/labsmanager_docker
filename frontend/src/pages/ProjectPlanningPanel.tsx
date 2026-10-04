import { Plus } from 'lucide-react'
import { useCallback, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { deleteProjectPlanningItem, getProjectPlanning, type PlanningMilestone, type PlanningFilters } from '../api/planning'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { FilterBar } from '../filters/FilterBar'
import { readFilterQuery } from '../filters/url'
import type { SupportedFilter } from '../filters/types'
import { adaptPlanningGantt } from '../gantt/PlanningGanttAdapter'
import { PlanningGanttView } from '../gantt/PlanningGanttView'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { MilestoneDetailSheet } from './MilestoneDetailSheet'
import { PlanningMilestoneFormSheet } from './PlanningMilestoneFormSheet'
import { PlanningMilestoneTable, type PlanningMilestoneActions } from './PlanningMilestoneTable'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeDetailPage.module.css'

export function ProjectPlanningPanel({ projectId, contextName }: { projectId: string; contextName?: string }) {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [mode, setMode] = useState<'list' | 'gantt'>('list')
  const [selected, setSelected] = useState<PlanningMilestone | null>(null)
  const [editing, setEditing] = useState<PlanningMilestone | 'new' | null>(null)
  const [deleting, setDeleting] = useState<PlanningMilestone | null>(null)
  const [months, setMonths] = useState<6 | 12 | 24 | 60 | 120>(24)
  const [anchor, setAnchor] = useState(() => new Date())
  const focus = useRef<HTMLElement | null>(null)
  const addButton = useRef<HTMLButtonElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const focusHandoff = useRef(false)
  const remove = useMutation()
  const catalogue: SupportedFilter[] = [
    { id: 'search', label: t('planning.search'), category: t('filters.categoryProject'), type: 'text', parameter: 'search' },
    { id: 'kind', label: t('planning.itemKind'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'kind', options: [
      { value: 'task', label: t('employee.task') }, { value: 'milestone', label: t('employee.milestone') },
    ] },
    { id: 'employee', label: t('employee.assignees'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'employee', source: 'participants' },
  ]
  const active = readFilterQuery(catalogue, searchParams)
  const filterKey = active.toString()
  const loader = useCallback((_key: string, signal: AbortSignal) => {
    const params = new URLSearchParams(filterKey)
    const filters: PlanningFilters = { search: params.get('search') || undefined, kind: (params.get('kind') || undefined) as PlanningFilters['kind'], employee: params.get('employee') || undefined }
    return getProjectPlanning(projectId, filters, signal)
  }, [projectId, filterKey])
  const resource = useEmployeeResource(`${projectId}:${filterKey}`, loader)
  const items = resource.data?.items ?? null
  const ganttData = useMemo(() => adaptPlanningGantt(items ?? []), [items])

  function openEdit(item: PlanningMilestone) { focusHandoff.current = true; setSelected(null); setEditing(item) }
  function openDelete(item: PlanningMilestone) { focusHandoff.current = true; setSelected(null); setDeleting(item) }
  const actions: PlanningMilestoneActions = {
    canChange: !!resource.data?.capabilities.can_change,
    canDelete: !!resource.data?.capabilities.can_delete,
    onEdit: openEdit, onDelete: openDelete,
    onTrigger: (trigger) => { focus.current = trigger },
    onMenuOpen: () => { focusHandoff.current = false },
    finalFocus: () => !focusHandoff.current,
  }
  async function confirmDelete() {
    if (!deleting) return
    const result = await remove.run(() => deleteProjectPlanningItem(projectId, deleting.id))
    if (result) {
      focus.current = addButton.current ?? section.current
      resource.updateData((previous) => ({ ...previous, items: previous.items.filter((item) => item.id !== deleting.id) }))
      setDeleting(null)
      void resource.refresh()
    }
  }
  const deleteError = remove.error ? normalizeMutationError(remove.error) : null

  return <section ref={section} tabIndex={-1} aria-label={t('project.tasks')}>
    <div className={styles.projectHeading}><h2 className={styles.panelTitle}>{t('project.tasks')}</h2>
      <div aria-label={t('gantt.view')} role="group"><Button aria-pressed={mode === 'list'} onClick={() => setMode('list')} size="sm" variant={mode === 'list' ? 'secondary' : 'ghost'}>{t('gantt.list')}</Button><Button aria-pressed={mode === 'gantt'} onClick={() => setMode('gantt')} size="sm" variant={mode === 'gantt' ? 'secondary' : 'ghost'}>{t('gantt.title')}</Button></div>
    </div>
    <FilterBar catalogue={catalogue} sources={{}} choiceOptions={{ participants: resource.data?.participants.map((person) => ({ value: String(person.id), label: `${person.first_name} ${person.last_name}` })) ?? [] }} query={searchParams} onChange={setSearchParams} />
    {resource.data?.capabilities.can_add && <Button ref={addButton} variant="ghost" size="sm" onClick={() => { focus.current = addButton.current; setEditing('new') }}><Plus aria-hidden="true" />{t('planning.createItem')}</Button>}
    {Boolean(resource.refreshError) && <Alert tone="warning">{t('genericInfo.refreshFailed')} <Button onClick={() => void resource.refresh()} variant="ghost">{t('common.retry')}</Button></Alert>}
    {mode === 'list' ? <PlanningMilestoneTable resource={{ data: items, error: resource.error, loading: resource.loading, retry: resource.retry }} onOpen={setSelected} actions={actions} /> : <div>
      {Boolean(resource.error) && <Alert tone="danger">{t('employee.secondaryError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
      {resource.loading && <p role="status">{t('gantt.loading')}</p>}
      <PlanningGanttView data={items ? ganttData : null} events={[]} anchor={anchor} months={months} onAnchorChange={setAnchor} onMonthsChange={setMonths} printTitle={`${t('project.tasks')} — ${contextName ?? projectId}`} printFilters={Object.fromEntries(new URLSearchParams(filterKey))} onSelect={(identity) => { if (identity.kind === 'work') setSelected(items?.find((item) => String(item.id) === identity.id) ?? null) }} />
    </div>}
    <MilestoneDetailSheet milestone={selected} onClose={() => setSelected(null)} onDependenciesChanged={() => void resource.refresh()} actions={actions} manageDependencies />
    {editing && <PlanningMilestoneFormSheet key={editing === 'new' ? 'new' : editing.id} projectId={projectId} item={editing === 'new' ? null : editing} participants={resource.data?.participants ?? []} returnFocus={focus} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); void resource.refresh() }} />}
    {deleting && <ConfirmDialog title={t('planning.deleteItemTitle')} description={t('planning.deleteItemDescription', { name: deleting.name })} pending={remove.pending} onCancel={() => setDeleting(null)} onConfirm={() => void confirmDelete()} returnFocus={focus} error={deleteError && <Alert tone="danger">{[...deleteError.messages, ...Object.values(deleteError.fields).flat()].join(' ') || t(`genericInfo.error.${deleteError.kind}`)}</Alert>} />}
  </section>
}
