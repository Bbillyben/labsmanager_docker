import { useState, type FormEvent, type RefObject } from 'react'
import type { PlanningMilestone, PlanningMilestoneWrite, ProjectPlanningCollection } from '../api/planning'
import { createProjectPlanningItem, updateProjectPlanningItem } from '../api/planning'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { CheckboxRow } from '../components/CheckboxRow'
import { Input } from '../components/ui/input'
import { NativeSelect } from '../components/ui/native-select'
import { Textarea } from '../components/ui/textarea'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import styles from './ProjectOverview.module.css'

export function PlanningMilestoneFormSheet({ projectId, item, participants, onClose, onSaved, returnFocus }: {
  projectId: string; item: PlanningMilestone | null; participants: ProjectPlanningCollection['participants']
  onClose: () => void; onSaved: (item: PlanningMilestone) => void; returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [kind, setKind] = useState<PlanningMilestone['work_kind']>(item?.work_kind ?? 'task')
  const [name, setName] = useState(item?.name ?? '')
  const [desc, setDesc] = useState(item?.desc ?? '')
  const [startDate, setStartDate] = useState(item?.start_date ?? '')
  const [endDate, setEndDate] = useState(item?.end_date ?? '')
  const [type, setType] = useState<PlanningMilestone['type']>(item?.type ?? 'o')
  const [percent, setPercent] = useState(item ? String(Number(item.quotity) * 100) : '0')
  const [status, setStatus] = useState(item?.status ?? false)
  const [employeeIds, setEmployeeIds] = useState<number[]>(() => item?.employees.filter((employee) => participants.some((participant) => participant.id === employee.id)).map((employee) => employee.id) ?? [])
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null

  function chooseKind(next: PlanningMilestone['work_kind']) {
    setKind(next)
    if (next === 'milestone') setStartDate('')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const payload: PlanningMilestoneWrite = {
      name, desc: desc || null, work_kind: kind,
      ...(kind === 'task' ? { start_date: startDate } : {}),
      end_date: endDate || null, type, quotity: type === 'q' ? (Number(percent) / 100).toFixed(3) : '0.000', status, employee_ids: employeeIds,
    }
    const result = await mutation.run(() => item
      ? updateProjectPlanningItem(projectId, item.id, payload)
      : createProjectPlanningItem(projectId, payload))
    if (result) onSaved(result.data)
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}>
    <SheetContent finalFocus={returnFocus}>
      <SheetHeader><SheetTitle>{t(item ? 'planning.editItem' : 'planning.createItem')}</SheetTitle>
        <SheetDescription>{t('planning.formDescription')}</SheetDescription></SheetHeader>
      <form className={styles.form} onSubmit={(event) => void submit(event)} aria-busy={mutation.pending}>
        {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t(`genericInfo.error.${error.kind}`)}</Alert>}
        <label>{t('planning.itemKind')}<NativeSelect value={kind} disabled={mutation.pending} onChange={(event) => chooseKind(event.target.value as PlanningMilestone['work_kind'])}>
          <option value="task">{t('employee.task')}</option><option value="milestone">{t('employee.milestone')}</option>
        </NativeSelect></label>
        <label>{t('planning.itemName')}<Input required maxLength={100} value={name} disabled={mutation.pending} onChange={(event) => setName(event.target.value)} /></label>
        <label>{t('employee.description')}<Textarea value={desc} disabled={mutation.pending} onChange={(event) => setDesc(event.target.value)} /></label>
        {kind === 'task' && <label>{t('employee.startDate')}<Input required type="date" value={startDate} disabled={mutation.pending} onChange={(event) => setStartDate(event.target.value)} /></label>}
        <label>{t('employee.deadline')}<Input type="date" value={endDate} disabled={mutation.pending} onChange={(event) => setEndDate(event.target.value)} /></label>
        <label>{t('employee.milestoneType')}<NativeSelect value={type} disabled={mutation.pending} onChange={(event) => setType(event.target.value as PlanningMilestone['type'])}>
          <option value="o">{t('employee.notQuantifiable')}</option><option value="q">{t('employee.quantifiable')}</option>
        </NativeSelect></label>
        {type === 'q' && <label>{t('employee.progress')} (%)<Input type="number" min="0" max="100" step="0.1" required value={percent} disabled={mutation.pending} onChange={(event) => setPercent(event.target.value)} /></label>}
        <CheckboxRow checked={status} disabled={mutation.pending} onChange={(event) => setStatus(event.target.checked)}>{t('planning.completed')}</CheckboxRow>
        <fieldset className="grid gap-1"><legend>{t('employee.assignees')}</legend>
          {participants.length ? participants.map((participant) => 
            <CheckboxRow key={participant.id} checked={employeeIds.includes(participant.id)} disabled={mutation.pending} onChange={(event) => setEmployeeIds((current) => event.target.checked 
                ? [...current, participant.id] : current.filter((id) => id !== participant.id))}>
              {participant.first_name} {participant.last_name}
              </CheckboxRow>) : <p>{t('planning.noParticipants')}</p>}
        </fieldset>
        <div className={styles.formButtons}><Button type="button" variant="ghost" disabled={mutation.pending} onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || !name.trim() || (kind === 'task' && !startDate)}>{t('common.save')}</Button></div>
      </form>
    </SheetContent>
  </Sheet>
}
