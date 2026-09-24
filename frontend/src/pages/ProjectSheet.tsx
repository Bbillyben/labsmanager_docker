import { X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { createProject, updateProject, type ProjectItem, type ProjectWrite } from '../api/projects'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function ProjectSheet({ project, onClose, onSaved }: { project: ProjectItem | null; onClose: () => void; onSaved: (id: number, created: boolean) => void }) {
  const [draft, setDraft] = useState<ProjectWrite>({ name: project?.name ?? '', start_date: project?.start_date ?? null, end_date: project?.end_date ?? null, status: project?.status ?? true })
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const message = error && (error.messages.join(' ') || Object.values(error.fields).flat().join(' ') || 'Impossible d’enregistrer le projet.')
  const change = <K extends keyof ProjectWrite>(key: K, value: ProjectWrite[K]) => setDraft((current) => ({ ...current, [key]: value }))

  async function save(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => project ? updateProject(project.id, draft) : createProject(draft))
    if (result) onSaved(result.data.id, !project)
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}>
    <SheetContent>
      <Button aria-label="Fermer" className="absolute right-4 top-4" disabled={mutation.pending} onClick={onClose} size="icon-sm" variant="ghost"><X /></Button>
      <SheetHeader><SheetTitle>{project ? 'Modifier le projet' : 'Ajouter un projet'}</SheetTitle><SheetDescription>{project ? project.name : 'Renseignez les informations du projet.'}</SheetDescription></SheetHeader>
      <form className="grid gap-3" aria-busy={mutation.pending} onSubmit={(event) => void save(event)}>
        {message && <Alert tone="danger">{message}</Alert>}
        <label className="grid gap-1">Nom du projet<InputField required maxLength={50} disabled={Boolean(project)} value={draft.name} onChange={(value) => change('name', value)} /></label>
        <label className="grid gap-1">Date de début<InputField type="date" value={draft.start_date ?? ''} onChange={(value) => change('start_date', value || null)} /></label>
        <label className="grid gap-1">Date de fin<InputField type="date" value={draft.end_date ?? ''} onChange={(value) => change('end_date', value || null)} /></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={draft.status} onChange={(event) => change('status', event.target.checked)} /> Actif</label>
        <div className="flex justify-end gap-2"><Button disabled={mutation.pending} onClick={onClose} type="button" variant="ghost">Annuler</Button><Button disabled={mutation.pending || !draft.name.trim()} type="submit">{mutation.pending ? 'Enregistrement…' : 'Enregistrer'}</Button></div>
      </form>
    </SheetContent>
  </Sheet>
}

function InputField({ onChange, ...props }: Omit<React.ComponentProps<'input'>, 'onChange'> & { onChange: (value: string) => void }) {
  return <input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" onChange={(event) => onChange(event.target.value)} {...props} />
}
