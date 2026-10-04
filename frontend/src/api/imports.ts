import { apiFileRequest, apiRequest } from './client'

export type ImportProfile = { key: string; label: string; description: string; formats: string[]; template_formats: string[]; preview_columns: { key: string; label: string }[] }
export type ImportStructure = { expected: string[]; recognized: string[]; missing: string[]; extra: string[]; columns: number; rows: number }
export type ImportRow = { row_number: number; state: 'new' | 'update' | 'unchanged' | 'error'; identity: string; summary: string; error_message: string; diff: { field: string; old: string; new: string }[]; values: Record<string, string> }
export type ImportResult = { summary: Record<ImportRow['state'], number>; rows: ImportRow[]; global_errors: string[]; can_commit: boolean; structure?: ImportStructure; sheet?: string; import_token?: string }
export type ImportUpload = { import_token: string; filename: string; size: number; format: string; sheets: string[]; structure: ImportStructure; sheet_structures: Record<string, ImportStructure> }

const path = (profile: string, action: string) => `/api/v1/imports/${encodeURIComponent(profile)}/${action}/`
export const getImportProfiles = () => apiRequest<{ items: ImportProfile[] }>('/api/v1/imports/profiles/')
export const getImportTemplate = (profile: string, format: string) => apiFileRequest(`${path(profile, 'template')}?format=${encodeURIComponent(format)}`, { method: 'GET' })
export const uploadImport = (profile: string, file: File) => { const body = new FormData(); body.set('file', file); return apiRequest<ImportUpload>(path(profile, 'upload'), { method: 'POST', body }) }
export const previewImport = (profile: string, importToken: string, sheet: string) => apiRequest<ImportResult>(path(profile, 'preview'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ import_token: importToken, sheet }) })
export const commitImport = (profile: string, importToken: string) => apiRequest<ImportResult>(path(profile, 'commit'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ import_token: importToken }) })
export const downloadImportErrors = (profile: string, importToken: string) => apiFileRequest(`${path(profile, 'errors')}?import_token=${encodeURIComponent(importToken)}`, { method: 'GET' })
