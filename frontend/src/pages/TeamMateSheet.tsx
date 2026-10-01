import { useState, type FormEvent, type RefObject } from 'react'
import { addTeamMate, updateTeamMate, type TeamMate, type TeamMateWrite } from '../api/teams'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { EntitySearch } from '../filters/EntitySearch'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function TeamMateSheet({ teamId, mate, excludedEmployeeIds, onClose, onSaved, returnFocus }: {
  teamId: string
  mate: TeamMate | null
  excludedEmployeeIds: number[]
  onClose: () => void
  onSaved: () => void
  returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<TeamMateWrite>({ employee_id: mate?.employee.id ?? 0, start_date: mate?.start_date ?? null, end_date: mate?.end_date ?? null })
  const [employeeSource] = useState(() => ({
    ...employeeFilterSources.employees,
    async search(query: string, signal: AbortSignal) {
      const result = await employeeFilterSources.employees.search(query, signal)
      return { ...result, options: result.options.filter((option) => !excludedEmployeeIds.includes(Number(option.value))) }
    },
  }))
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!draft.employee_id) return
    const result = await mutation.run(() => mate ? updateTeamMate(teamId, mate.id, draft) : addTeamMate(teamId, draft))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(mate ? 'team.editMember' : 'team.addMember')}</SheetTitle><SheetDescription>{t('team.chooseEmployee')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}>
      {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('team.saveError')}</Alert>}
      <EntitySearch id="team-member" label={t('projectCalendar.employee')} value={draft.employee_id ? String(draft.employee_id) : ''} source={employeeSource} onChange={(value) => setDraft((current) => ({ ...current, employee_id: Number(value) }))} />
      <label className="grid gap-1">{t('team.startDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={draft.start_date ?? ''} onChange={(event) => setDraft((current) => ({ ...current, start_date: event.target.value || null }))} /></label>
      <label className="grid gap-1">{t('team.endDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={draft.end_date ?? ''} onChange={(event) => setDraft((current) => ({ ...current, end_date: event.target.value || null }))} /></label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={!draft.employee_id || mutation.pending}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
