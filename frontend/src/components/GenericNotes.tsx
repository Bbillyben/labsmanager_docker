import { Dialog } from '@base-ui/react/dialog'
import { Ellipsis, LockKeyhole, Pencil, Plus, Trash2 } from 'lucide-react'
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState, type FormEvent } from 'react'
import { createNote, deleteNote, getNotes, updateNote, type GenericNote, type NoteScope, type NoteVisibility } from '../api/notes'
import { normalizeMutationError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { useEmployeeResource } from '../pages/useEmployeeResource'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { ConfirmDialog } from './common/ConfirmDialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu'
import { ProseEditor } from './ProseEditor'

type Modal = 'create' | 'rename' | 'visibility' | null

export type GenericNotesHandle = { savePending: () => Promise<boolean> }

export const GenericNotes = forwardRef<GenericNotesHandle, { scope: NoteScope; objectId: string }>(function GenericNotes({ scope, objectId }, ref) {
  const { t, language } = useTranslation()
  const load = useCallback((_id: string, signal: AbortSignal) => getNotes(scope, objectId, signal), [scope, objectId])
  const resource = useEmployeeResource(`${scope}:${objectId}`, load)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const draftRef = useRef('')
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [modal, setModal] = useState<Modal>(null)
  const [name, setName] = useState('')
  const [visibility, setVisibility] = useState<NoteVisibility>('object')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const trigger = useRef<HTMLElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inFlight = useRef<Promise<boolean> | null>(null)
  const notes = resource.data?.items ?? []
  const selected = notes.find((note) => note.id === selectedId) ?? notes[0] ?? null
  const date = (value: string) => new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

  useEffect(() => { if (selected && selected.id !== selectedId) setSelectedId(selected.id) }, [selected, selectedId])
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  function replaceNote(note: GenericNote) {
    resource.updateData((current) => ({ ...current, items: current.items.map((item) => item.id === note.id ? note : item) }))
  }

  async function save(note: GenericNote): Promise<boolean> {
    if (timer.current) clearTimeout(timer.current)
    if (inFlight.current) await inFlight.current
    const html = draftRef.current
    if (html === note.note) return true
    setSaveState('saving')
    const operation = updateNote(scope, objectId, note.id, { note: html }).then((updated) => {
      replaceNote(updated)
      if (draftRef.current === html) setSaveState('saved')
      return true
    }).catch(() => { setSaveState('error'); return false })
    inFlight.current = operation
    const result = await operation
    if (inFlight.current === operation) inFlight.current = null
    return result
  }

  function changeDraft(html: string) {
    draftRef.current = html
    setDraft(html)
    setSaveState('idle')
    if (timer.current) clearTimeout(timer.current)
    if (selected) timer.current = setTimeout(() => { void save(selected) }, 1200)
  }

  async function finishEditing(): Promise<boolean> {
    if (!editing || !selected) return true
    const saved = await save(selected)
    if (saved) setEditing(false)
    return saved
  }

  useImperativeHandle(ref, () => ({ savePending: finishEditing }))

  async function choose(note: GenericNote) {
    if (note.id === selected?.id) return
    if (!await finishEditing()) return
    setSelectedId(note.id)
    draftRef.current = note.note
    setDraft(note.note)
    setSaveState('idle')
  }

  function beginEdit(note: GenericNote) {
    draftRef.current = note.note
    setDraft(note.note)
    setSaveState('idle')
    setEditing(true)
  }

  function openModal(kind: Modal) {
    setError(null)
    setName(kind === 'create' ? '' : selected?.name ?? '')
    setVisibility(kind === 'create' ? 'object' : selected?.visibility ?? 'object')
    setModal(kind)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!modal || pending) return
    setPending(true)
    setError(null)
    try {
      if (modal === 'create') {
        if (!await finishEditing()) { setError(t('notes.saveError')); return }
        const created = await createNote(scope, objectId, name, visibility)
        resource.updateData((current) => ({ ...current, items: [...current.items, created] }))
        setSelectedId(created.id)
        beginEdit(created)
      } else if (selected) {
        const updated = await updateNote(scope, objectId, selected.id, modal === 'rename' ? { name } : { visibility })
        replaceNote(updated)
      }
      setModal(null)
    } catch (cause) {
      const normalized = normalizeMutationError(cause)
      setError(normalized.fields.name?.includes('already_exists') ? t('notes.duplicate') : normalized.fields.name?.join(' ') || normalized.messages.join(' ') || t('notes.saveError'))
    } finally { setPending(false) }
  }

  async function remove() {
    if (!selected) return
    setPending(true)
    setError(null)
    try {
      await deleteNote(scope, objectId, selected.id)
      trigger.current = section.current
      resource.updateData((current) => ({ ...current, items: current.items.filter((note) => note.id !== selected.id) }))
      setSelectedId(null)
      setEditing(false)
      setDeleting(false)
    } catch { setError(t('notes.deleteError')) } finally { setPending(false) }
  }

  if (resource.loading) return <p role="status">{t('common.loading')}</p>
  if (resource.error || !resource.data) return <Alert tone="danger">{t('notes.loadError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  return <section ref={section} tabIndex={-1} aria-label={t('notes.title')} className="space-y-4">
    <div className="flex flex-wrap items-center gap-2 border-b border-border pb-2">
      <div role="tablist" aria-label={t('notes.title')} className="flex flex-1 flex-wrap gap-1">
        {notes.map((note) => <button key={note.id} type="button" role="tab" aria-selected={selected?.id === note.id} onClick={() => void choose(note)} className={`rounded-md px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-ring ${selected?.id === note.id ? 'bg-secondary font-semibold' : 'hover:bg-muted'}`}>{note.visibility === 'creator' && <LockKeyhole aria-label={t('notes.creatorOnly')} className="mr-1 inline size-3" />}{note.name}</button>)}
      </div>
      {resource.data.capabilities.can_add && <Button variant="secondary" size="sm" onClick={(event) => { trigger.current = event.currentTarget; openModal('create') }}><Plus aria-hidden="true" />{t('notes.add')}</Button>}
    </div>
    {!selected && <p className="text-sm text-muted-foreground">{t('notes.empty')}</p>}
    {selected && <div role="tabpanel" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{selected.name}</h2>
        <div className="flex items-center gap-2">
          {selected.capabilities.can_change && <Button variant="secondary" size="sm" onClick={() => editing ? void finishEditing() : beginEdit(selected)}><Pencil aria-hidden="true" />{t(editing ? 'notes.finish' : 'common.edit')}</Button>}
          {(selected.capabilities.can_rename || selected.capabilities.can_change_visibility || selected.capabilities.can_delete) && <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={t('notes.actions')} onClick={(event) => { trigger.current = event.currentTarget }}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
            <DropdownMenuContent align="end" finalFocus={() => modal || deleting ? false : true}>
              {selected.capabilities.can_rename && <DropdownMenuItem onClick={() => openModal('rename')}>{t('notes.rename')}</DropdownMenuItem>}
              {selected.capabilities.can_change_visibility && <DropdownMenuItem onClick={() => openModal('visibility')}>{t('notes.visibility')}</DropdownMenuItem>}
              {selected.capabilities.can_delete && <DropdownMenuItem onClick={() => { setError(null); setDeleting(true) }}><Trash2 aria-hidden="true" />{t('common.delete')}</DropdownMenuItem>}
            </DropdownMenuContent>
          </DropdownMenu>}
        </div>
      </div>
      {editing ? <>
        <ProseEditor key={selected.id} initialHtml={draft} onChange={changeDraft} />
        <p role="status" className="text-xs text-muted-foreground">{t(`notes.${saveState}`)}</p>
      </> : <div className="prose max-w-none min-h-24 rounded-md border border-border p-4" dangerouslySetInnerHTML={{ __html: selected.note }} />}
      <p className="text-xs text-muted-foreground">{t('notes.createdBy', { name: selected.creator.name, date: date(selected.created_at) })} · {t('notes.modified', { date: date(selected.updated_at) })}</p>
    </div>}
    {modal && <Dialog.Root open onOpenChange={(open) => { if (!open && !pending) setModal(null) }}><Dialog.Portal><Dialog.Backdrop className="fixed inset-0 z-50 bg-black/45" /><Dialog.Viewport className="fixed inset-0 z-50 flex items-center justify-center p-4"><Dialog.Popup finalFocus={trigger} className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-xl">
      <Dialog.Title className="text-lg font-semibold">{t(modal === 'create' ? 'notes.add' : modal === 'rename' ? 'notes.rename' : 'notes.visibility')}</Dialog.Title>
      <form className="mt-4 space-y-4" onSubmit={(event) => void submit(event)}>
        {error && <Alert tone="danger">{error}</Alert>}
        {modal !== 'visibility' && <label className="grid gap-1 text-sm">{t('notes.name')}<input autoFocus required maxLength={50} className="h-9 rounded-md border border-input bg-background px-3" value={name} onChange={(event) => setName(event.target.value)} /></label>}
        {modal !== 'rename' && <label className="grid gap-1 text-sm">{t('notes.visibility')}<select className="h-9 rounded-md border border-input bg-background px-3" value={visibility} onChange={(event) => setVisibility(event.target.value as NoteVisibility)}><option value="object">{t('notes.objectViewers')}</option><option value="creator">{t('notes.creatorOnly')}</option></select></label>}
        <div className="flex justify-end gap-2"><Button type="button" variant="ghost" disabled={pending} onClick={() => setModal(null)}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{t('common.save')}</Button></div>
      </form>
    </Dialog.Popup></Dialog.Viewport></Dialog.Portal></Dialog.Root>}
    {deleting && selected && <ConfirmDialog title={t('notes.deleteTitle')} description={t('notes.deleteDescription', { name: selected.name })} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} returnFocus={trigger} onCancel={() => setDeleting(false)} onConfirm={() => void remove()} />}
  </section>
})
