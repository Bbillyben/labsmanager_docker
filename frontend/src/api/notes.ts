import { apiRequest } from './client'

export type NoteScope = 'project' | 'employee' | 'team' | 'institution' | 'contract'
export type NoteVisibility = 'object' | 'creator'
export type NoteCapabilities = { can_add: boolean; can_change: boolean; can_rename: boolean; can_delete: boolean; can_change_visibility: boolean }
export type GenericNote = {
  id: number; admin_url?: string | null; name: string; note: string; visibility: NoteVisibility
  creator: { id: number; name: string }; created_at: string; updated_at: string
  capabilities: NoteCapabilities
}
export type NotesCollection = { capabilities: { can_add: boolean }; items: GenericNote[] }

const collection = (scope: NoteScope, id: string) => `/api/v1/notes/${scope}/${encodeURIComponent(id)}/`
const detail = (scope: NoteScope, id: string, noteId: number) => `${collection(scope, id)}${noteId}/`
const write = (method: 'POST' | 'PATCH', data: object) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })

export function getNotes(scope: NoteScope, id: string, signal: AbortSignal) { return apiRequest<NotesCollection>(collection(scope, id), { signal }) }
export function createNote(scope: NoteScope, id: string, name: string, visibility: NoteVisibility) { return apiRequest<GenericNote>(collection(scope, id), write('POST', { name, visibility })) }
export function updateNote(scope: NoteScope, id: string, noteId: number, data: { note?: string; name?: string; visibility?: NoteVisibility }) { return apiRequest<GenericNote>(detail(scope, id, noteId), write('PATCH', data)) }
export function deleteNote(scope: NoteScope, id: string, noteId: number) { return apiRequest<void>(detail(scope, id, noteId), { method: 'DELETE' }) }
