import { useTranslation } from '../i18n/i18n'
import { Plus } from 'lucide-react'
import { useRef, useState, type FormEvent, type RefObject } from 'react'
import { Link } from 'react-router-dom'
import { createProjectParticipant, deleteProjectParticipant, updateProjectParticipant, type ProjectOverview, type ProjectParticipant, type ProjectParticipantWrite } from '../api/projects'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { useSelectableItem } from '../components/useSelectableItem'
import { Input } from '../components/ui/input'
import { NativeSelect } from '../components/ui/native-select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { EntitySearch } from '../filters/EntitySearch'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import type { EmployeeResource } from './useEmployeeResource'
import styles from './ProjectOverview.module.css'

type Props = { projectId: string; resource: EmployeeResource<ProjectOverview> }
const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(`${value}T12:00:00`)) : '—'

export function ProjectParticipantBlock({ projectId, resource }: Props) {
  const { t, language } = useTranslation()
  const [editing, setEditing] = useState<ProjectParticipant | 'new' | null>(null)
  const [deleting, setDeleting] = useState<ProjectParticipant | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const { setSelectedId, containerRef, rowProps } = useSelectableItem()
  const data = resource.data?.participants
  if (!data) return null

  function upsert(item: ProjectParticipant) {
    resource.updateData((previous) => ({ ...previous, participants: { ...previous.participants, items: [...previous.participants.items.filter((entry) => entry.id !== item.id), item].sort((a, b) => a.employee.last_name.localeCompare(b.employee.last_name) || a.id - b.id) } }))
    setEditing(null)
    void resource.refresh()
  }
  function remove(id: number) {
    resource.updateData((previous) => ({ ...previous, participants: { ...previous.participants, items: previous.participants.items.filter((entry) => entry.id !== id) } }))
    setDeleting(null)
    void resource.refresh()
  }

  return <section ref={containerRef} className={`${styles.column} ${styles.section}`} aria-labelledby="project-participants-heading">
    <h3 id="project-participants-heading">{t('project.participants')}</h3>
    {data.items.length ? <ul className={styles.items}>{data.items.map((item) => {
      const name = `${item.employee.first_name} ${item.employee.last_name}`
      return <li className={styles.item} key={item.id} {...rowProps(item.id, data.capabilities.can_change || data.capabilities.can_delete)}>
        <div className={styles.itemMain}>
          {item.employee.can_view ? <Link to={`/employees/${item.employee.id}`}>{name}</Link> : <strong>{name}</strong>}
          <span>{t('project.participantRoleLabel', { role: t(item.status === 'l' ? 'project.leaderRole' : item.status === 'cl' ? 'project.coLeaderRole' : 'project.participantRole'), allocation: (Number(item.quotity) * 100).toFixed(1) })}</span>
          <small>{t('project.participantDates', { start: dateLabel(item.start_date, language), end: dateLabel(item.end_date, language), status: t(item.is_active ? 'common.active' : 'common.inactive') })}</small>
        </div>
        {(data.capabilities.can_change || data.capabilities.can_delete) && <div className={styles.actions}><ItemActionMenu label={t('common.actionsFor', { name })} canChange={data.capabilities.can_change} canDelete={data.capabilities.can_delete}
          onOpen={() => setSelectedId(item.id)} onEdit={() => { focus.current = containerRef.current; setEditing(item) }} onDelete={() => { focus.current = containerRef.current; setDeleting(item) }} /></div>}
      </li>
    })}</ul> : <p className={styles.empty}>{t('project.noParticipants')}</p>}
    {data.capabilities.can_add && <div className={styles.footer}><Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditing('new') }}><Plus aria-hidden="true" />{t('project.addParticipant')}</Button></div>}
    {editing && <ParticipantSheet projectId={projectId} item={editing === 'new' ? null : editing} project={resource.data!} onClose={() => setEditing(null)} onSaved={upsert} />}
    {deleting && <DeleteParticipant projectId={projectId} item={deleting} focus={focus} onClose={() => setDeleting(null)} onDeleted={() => remove(deleting.id)} />}
  </section>
}

function ParticipantSheet({ projectId, project, item, onClose, onSaved }: { projectId: string; project: ProjectOverview; item: ProjectParticipant | null; onClose: () => void; onSaved: (item: ProjectParticipant) => void }) {
  const { t } = useTranslation()
  const [employeeId, setEmployeeId] = useState(item ? String(item.employee.id) : '')
  const [status, setStatus] = useState<ProjectParticipant['status']>(item?.status ?? 'p')
  const [startDate, setStartDate] = useState(item?.start_date ?? project.start_date ?? '')
  const [endDate, setEndDate] = useState(item?.end_date ?? project.end_date ?? '')
  const [percent, setPercent] = useState(item ? String(Number(item.quotity) * 100) : '0')
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null

  async function save(event: FormEvent) {
    event.preventDefault()
    const value: ProjectParticipantWrite = {
      status, start_date: startDate || null, end_date: endDate || null,
      quotity: (Number(percent) / 100).toFixed(3),
      ...(!item && { employee_id: Number(employeeId) }),
    }
    const result = await mutation.run(() => item ? updateProjectParticipant(projectId, item.id, value) : createProjectParticipant(projectId, value))
    if (result) onSaved(result.data)
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent>
    <SheetHeader><SheetTitle>{t(item ? 'project.editParticipant' : 'project.addParticipant')}</SheetTitle><SheetDescription>{item ? `${item.employee.first_name} ${item.employee.last_name}` : t('project.associateEmployee')}</SheetDescription></SheetHeader>
    <form className={styles.form} aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
      {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('project.participantSaveError')}</Alert>}
      {item ? <p>{t('project.employeeLabel')} <strong>{item.employee.first_name} {item.employee.last_name}</strong></p> : <label>{t('project.employee')}<EntitySearch id="project-participant-employee" label={t('project.employee')} value={employeeId} source={employeeFilterSources.allEmployees} placeholder={t('project.employeeSearch')} onChange={setEmployeeId} /></label>}
      <label>{t('project.role')}<NativeSelect value={status} disabled={mutation.pending} onChange={(event) => setStatus(event.target.value as ProjectParticipant['status'])}><option value="p">{t('project.participantRole')}</option><option value="cl">{t('project.coLeaderRole')}</option><option value="l">{t('project.leaderRole')}</option></NativeSelect></label>
      <label>{t('project.startDate')}<Input type="date" value={startDate} disabled={mutation.pending} onChange={(event) => setStartDate(event.target.value)} /></label>
      <label>{t('project.endDate')}<Input type="date" value={endDate} disabled={mutation.pending} onChange={(event) => setEndDate(event.target.value)} /></label>
      <label>{t('project.allocation')}<Input type="number" min="0" max="100" step="0.1" required value={percent} disabled={mutation.pending} onChange={(event) => setPercent(event.target.value)} /></label>
      <div className={styles.formButtons}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!item && !employeeId) || percent === ''}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}

function DeleteParticipant({ projectId, item, focus, onClose, onDeleted }: { projectId: string; item: ProjectParticipant; focus: RefObject<HTMLElement | null>; onClose: () => void; onDeleted: () => void }) {
  const { t } = useTranslation()
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() { const result = await mutation.run(() => deleteProjectParticipant(projectId, item.id)); if (result) onDeleted() }
  return <ConfirmDialog title={t('project.deleteParticipant')} description={t('project.removeParticipant', { name: `${item.employee.first_name} ${item.employee.last_name}` })} pending={mutation.pending} error={error && <Alert tone="danger">{error.messages.join(' ') || t('project.institutionDeleteError')}</Alert>} onCancel={onClose} onConfirm={() => void remove()} returnFocus={focus} />
}
