import { useState, type FormEvent, type RefObject } from 'react'
import { createTeam, updateTeam, type Team, type TeamListResponse } from '../api/teams'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { employeeFilterSources } from '../config/employeeFilterSources'
import { EntitySearch } from '../filters/EntitySearch'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function TeamFormSheet({ team, createCapabilities, onClose, onSaved, returnFocus }: {
  team: Team | null
  createCapabilities?: TeamListResponse['capabilities']
  onClose: () => void
  onSaved: (saved: Team) => void
  returnFocus?: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [name, setName] = useState(team?.name ?? '')
  const [leaderId, setLeaderId] = useState(String(team?.leader.id ?? createCapabilities?.default_leader?.id ?? ''))
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || !leaderId) return
    const data = { name: name.trim(), leader_id: Number(leaderId) }
    const result = await mutation.run(() => team ? updateTeam(String(team.id), data) : createTeam(data))
    if (result) onSaved(result.data)
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(team ? 'team.editTeam' : 'team.addTeam')}</SheetTitle><SheetDescription>{t('team.formDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}>
      {error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ') || t('team.saveError')}</Alert>}
      <label className="grid gap-1">{t('team.name')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" maxLength={70} required value={name} onChange={(event) => setName(event.target.value)} /></label>
      {createCapabilities && !createCapabilities.can_choose_leader ? <p>{t('team.leader')}: {createCapabilities.default_leader?.name}</p> : <EntitySearch id="team-leader" label={t('team.leader')} value={leaderId} source={employeeFilterSources.employees} onChange={setLeaderId} />}
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={!name.trim() || !leaderId || mutation.pending}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
