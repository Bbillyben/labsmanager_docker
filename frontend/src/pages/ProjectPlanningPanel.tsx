import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { deleteProjectPlanningItem, getProjectPlanning, type PlanningMilestone, type PlanningFilters } from '../api/planning'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { FilterBar } from '../filters/FilterBar'
import { readFilterQuery } from '../filters/url'
import type { SupportedFilter } from '../filters/types'
import { adaptPlanningGantt } from '../gantt/PlanningGanttAdapter'
import { LabsManagerGantt } from '../gantt/LabsManagerGantt'
import type { GanttWindow } from '../gantt/SvarGanttAdapter'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { MilestoneDetailSheet } from './MilestoneDetailSheet'
import { PlanningMilestoneFormSheet } from './PlanningMilestoneFormSheet'
import { PlanningMilestoneTable, type PlanningMilestoneActions } from './PlanningMilestoneTable'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeDetailPage.module.css'
import ganttStyles from '../gantt/EmployeeGanttPanel.module.css'

const iso = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`

export function ProjectPlanningPanel({ projectId }: { projectId: string }) {
  const { t, language } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [mode, setMode] = useState<'list' | 'gantt'>('list')
  const [selected, setSelected] = useState<PlanningMilestone | null>(null)
  const [editing, setEditing] = useState<PlanningMilestone | 'new' | null>(null)
  const [deleting, setDeleting] = useState<PlanningMilestone | null>(null)
  const [months, setMonths] = useState<6 | 12 | 24 | 60 | 120>(24)
  const [anchor, setAnchor] = useState(() => new Date())
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
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
  const window = useMemo<GanttWindow>(() => {
    const from = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
    const to = new Date(from.getFullYear(), from.getMonth() + months, 0)
    return { from: iso(from), to: iso(to), months }
  }, [anchor, months])

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.classList.contains('dark')))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

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
  const step = months === 6 ? 3 : months === 12 ? 6 : months === 120 ? 24 : 12
  const move = (direction: number) => setAnchor((current) => new Date(current.getFullYear(), current.getMonth() + direction * step, 1))
  const rangeLabel = `${new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(new Date(`${window.from}T12:00:00`))} – ${new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(new Date(`${window.to}T12:00:00`))}`

  return <section ref={section} tabIndex={-1} aria-label={t('project.tasks')}>
    <div className={styles.projectHeading}><h2 className={styles.panelTitle}>{t('project.tasks')}</h2>
      <div aria-label={t('gantt.view')} role="group"><Button aria-pressed={mode === 'list'} onClick={() => setMode('list')} size="sm" variant={mode === 'list' ? 'secondary' : 'ghost'}>{t('gantt.list')}</Button><Button aria-pressed={mode === 'gantt'} onClick={() => setMode('gantt')} size="sm" variant={mode === 'gantt' ? 'secondary' : 'ghost'}>{t('gantt.title')}</Button></div>
    </div>
    <FilterBar catalogue={catalogue} sources={{}} choiceOptions={{ participants: resource.data?.participants.map((person) => ({ value: String(person.id), label: `${person.first_name} ${person.last_name}` })) ?? [] }} query={searchParams} onChange={setSearchParams} />
    {resource.data?.capabilities.can_add && <Button ref={addButton} variant="ghost" size="sm" onClick={() => { focus.current = addButton.current; setEditing('new') }}><Plus aria-hidden="true" />{t('planning.createItem')}</Button>}
    {Boolean(resource.refreshError) && <Alert tone="warning">{t('genericInfo.refreshFailed')} <Button onClick={() => void resource.refresh()} variant="ghost">{t('common.retry')}</Button></Alert>}
    {mode === 'list' ? <PlanningMilestoneTable resource={{ data: items, error: resource.error, loading: resource.loading, retry: resource.retry }} onOpen={setSelected} actions={actions} /> : <div className={ganttStyles.root}>
      <div className={ganttStyles.toolbar}><div className={ganttStyles.group}>
        <Button aria-label={t('gantt.previous')} onClick={() => move(-1)} size="icon-sm" variant="ghost"><ChevronLeft aria-hidden="true" /></Button>
        <Button onClick={() => setAnchor(new Date())} size="sm" variant="ghost">{t('gantt.current')}</Button>
        <Button aria-label={t('gantt.next')} onClick={() => move(1)} size="icon-sm" variant="ghost"><ChevronRight aria-hidden="true" /></Button><strong>{rangeLabel}</strong>
      </div><div aria-label={t('gantt.period')} className={ganttStyles.group} role="group">{([6, 12, 24, 60, 120] as const).map((value) => <Button aria-pressed={months === value} key={value} onClick={() => setMonths(value)} size="sm" variant={months === value ? 'secondary' : 'ghost'}>{t(`gantt.months${value}`)}</Button>)}</div></div>
      {Boolean(resource.error) && <Alert tone="danger">{t('employee.secondaryError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
      {resource.loading && <p role="status">{t('gantt.loading')}</p>}
      {items && <LabsManagerGantt data={ganttData} events={[]} dark={dark} window={window} onSelect={(identity) => { if (identity.kind === 'work') setSelected(items.find((item) => String(item.id) === identity.id) ?? null) }} />}
    </div>}
    <MilestoneDetailSheet milestone={selected} onClose={() => setSelected(null)} onDependenciesChanged={() => void resource.refresh()} actions={actions} manageDependencies />
    {editing && <PlanningMilestoneFormSheet key={editing === 'new' ? 'new' : editing.id} projectId={projectId} item={editing === 'new' ? null : editing} participants={resource.data?.participants ?? []} returnFocus={focus} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); void resource.refresh() }} />}
    {deleting && <ConfirmDialog title={t('planning.deleteItemTitle')} description={t('planning.deleteItemDescription', { name: deleting.name })} pending={remove.pending} onCancel={() => setDeleting(null)} onConfirm={() => void confirmDelete()} returnFocus={focus} error={deleteError && <Alert tone="danger">{[...deleteError.messages, ...Object.values(deleteError.fields).flat()].join(' ') || t(`genericInfo.error.${deleteError.kind}`)}</Alert>} />}
  </section>
}
