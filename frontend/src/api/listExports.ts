import { apiFileRequest } from './client'

export type ListExportEntity = 'employees' | 'projects' | 'teams' | 'contracts' | 'fund-items' | 'budgets' | 'expenses'
export type ListExportFormat = 'xlsx' | 'csv' | 'tsv' | 'xls'

export function listExportUrl(entity: ListExportEntity, listQuery: string, format: ListExportFormat) {
  const query = new URLSearchParams(listQuery)
  for (const key of ['offset', 'limit', 'page', 'page_size', 'filters_initialized']) query.delete(key)
  for (const [key, value] of [...query]) if (!value) query.delete(key)
  query.set('format', format)
  return `/api/v1/${entity}/export/?${query}`
}

export function exportList(entity: ListExportEntity, listQuery: string, format: ListExportFormat) {
  return apiFileRequest(listExportUrl(entity, listQuery, format), { method: 'GET' })
}
