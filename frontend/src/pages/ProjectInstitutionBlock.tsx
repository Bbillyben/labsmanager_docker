import { useTranslation } from '../i18n/i18n'
import { Plus } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { createProjectInstitution, deleteProjectInstitution, getProjectOverviewOptions, updateProjectInstitution, type ProjectInstitution, type ProjectOverview } from '../api/projects'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { useSelectableItem } from '../components/useSelectableItem'
import { NativeSelect } from '../components/ui/native-select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import type { EmployeeResource } from './useEmployeeResource'
import styles from './ProjectOverview.module.css'

type Props = { projectId: string; resource: EmployeeResource<ProjectOverview> }

export function ProjectInstitutionBlock({ projectId, resource }: Props) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState<ProjectInstitution | 'new' | null>(null)
  const [deleting, setDeleting] = useState<ProjectInstitution | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const { setSelectedId, containerRef, rowProps } = useSelectableItem()
  const data = resource.data?.institutions
  if (!data) return null

  function upsert(item: ProjectInstitution) {
    resource.updateData((previous) => ({ ...previous, institutions: { ...previous.institutions, items: [...previous.institutions.items.filter((entry) => entry.id !== item.id), item].sort((a, b) => a.institution.short_name.localeCompare(b.institution.short_name)) } }))
    setEditing(null)
    void resource.refresh()
  }
  function remove(id: number) {
    resource.updateData((previous) => ({ ...previous, institutions: { ...previous.institutions, items: previous.institutions.items.filter((entry) => entry.id !== id) } }))
    setDeleting(null)
    void resource.refresh()
  }

  return <section ref={containerRef} className={`${styles.column} ${styles.section}`} aria-labelledby="project-institutions-heading">
    <h3 id="project-institutions-heading">{t('project.institutions')}</h3>
    {data.items.length ? <ul className={styles.items}>{data.items.map((item) => <li className={styles.item} key={item.id} {...rowProps(item.id, data.capabilities.can_change || data.capabilities.can_delete)}>
      <div className={styles.itemMain}><strong>{item.institution.short_name}</strong><span>{item.institution.name}</span><small>{t(item.status === 'c' ? 'project.institutionCoordinator' : 'project.institutionParticipant')}</small></div>
      {(data.capabilities.can_change || data.capabilities.can_delete) && <div className={styles.actions}><ItemActionMenu label={t('common.actionsFor', { name: item.institution.short_name })} canChange={data.capabilities.can_change} canDelete={data.capabilities.can_delete}
        onOpen={() => setSelectedId(item.id)} onEdit={() => { focus.current = containerRef.current; setEditing(item) }} onDelete={() => { focus.current = containerRef.current; setDeleting(item) }} /></div>}
    </li>)}</ul> : <p className={styles.empty}>{t('project.noInstitutions')}</p>}
    {data.capabilities.can_add && <div className={styles.footer}><Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditing('new') }}><Plus aria-hidden="true" />{t('project.addInstitution')}</Button></div>}
    {editing && <InstitutionSheet projectId={projectId} item={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={upsert} />}
    {deleting && <DeleteInstitution projectId={projectId} item={deleting} focus={focus} onClose={() => setDeleting(null)} onDeleted={() => remove(deleting.id)} />}
  </section>
}

function InstitutionSheet({ projectId, item, onClose, onSaved }: { projectId: string; item: ProjectInstitution | null; onClose: () => void; onSaved: (item: ProjectInstitution) => void }) {
  const { t } = useTranslation()
  const [institutionId, setInstitutionId] = useState(item ? String(item.institution.id) : '')
  const [status, setStatus] = useState<ProjectInstitution['status']>(item?.status ?? 'p')
  const [options, setOptions] = useState<Array<{ id: number; short_name: string; name: string }> | null>(null)
  const [optionsError, setOptionsError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  useEffect(() => {
    if (item) return
    const controller = new AbortController()
    getProjectOverviewOptions(projectId, controller.signal).then(
      (value) => { if (!controller.signal.aborted) { setOptions(value.institutions); setOptionsError(false) } },
      () => { if (!controller.signal.aborted) setOptionsError(true) },
    )
    return () => controller.abort()
  }, [projectId, item, attempt])
  async function save(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => item ? updateProjectInstitution(projectId, item.id, { status }) : createProjectInstitution(projectId, { institution_id: Number(institutionId), status }))
    if (result) onSaved(result.data)
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent>
    <SheetHeader><SheetTitle>{t(item ? 'project.editInstitution' : 'project.addInstitution')}</SheetTitle><SheetDescription>{item ? item.institution.name : t('project.associateInstitution')}</SheetDescription></SheetHeader>
    <form className={styles.form} aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
      {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('project.institutionSaveError')}</Alert>}
      {item ? <p>{t('project.institutionLabel')} <strong>{item.institution.name}</strong></p> : <label>{t('project.institution')}
        {optionsError ? <Alert tone="danger">{t('project.catalogueUnavailable')} <Button variant="ghost" onClick={() => setAttempt((value) => value + 1)}>{t('common.retry')}</Button></Alert> : <NativeSelect required value={institutionId} disabled={mutation.pending || !options} onChange={(event) => setInstitutionId(event.target.value)}><option value="">{t('common.choose')}</option>{options?.map((option) => <option key={option.id} value={option.id}>{option.short_name} — {option.name}</option>)}</NativeSelect>}
      </label>}
      <label>{t('project.institutionRole')}<NativeSelect value={status} disabled={mutation.pending} onChange={(event) => setStatus(event.target.value as ProjectInstitution['status'])}><option value="p">{t('project.institutionParticipant')}</option><option value="c">{t('project.institutionCoordinator')}</option></NativeSelect></label>
      <div className={styles.formButtons}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!item && !institutionId)}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}

function DeleteInstitution({ projectId, item, focus, onClose, onDeleted }: { projectId: string; item: ProjectInstitution; focus: React.RefObject<HTMLElement | null>; onClose: () => void; onDeleted: () => void }) {
  const { t } = useTranslation()
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() { const result = await mutation.run(() => deleteProjectInstitution(projectId, item.id)); if (result) onDeleted() }
  return <ConfirmDialog title={t('project.deleteInstitution')} description={t('project.removeInstitution', { name: item.institution.name })} pending={mutation.pending} error={error && <Alert tone="danger">{error.messages.join(' ') || t('project.institutionDeleteError')}</Alert>} onCancel={onClose} onConfirm={() => void remove()} returnFocus={focus} />
}
