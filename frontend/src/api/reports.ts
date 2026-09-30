import { apiFileRequest, apiRequest } from './client'

export type ReportEntity = 'project' | 'employee'
export type ReportFormat = 'word' | 'pdf'
export type ReportTemplate = { id: number; name: string }
export type ReportExportWrite = { template_id: number; start_date?: string | null; end_date?: string | null }

const path = (entity: ReportEntity, id: number, format: ReportFormat) => `/api/v1/reports/${entity}/${id}/${format}/`

export function getReportTemplates(entity: ReportEntity, id: number, format: ReportFormat, signal: AbortSignal) {
  return apiRequest<{ templates: ReportTemplate[] }>(path(entity, id, format), { signal })
}

export function exportReport(entity: ReportEntity, id: number, format: ReportFormat, value: ReportExportWrite) {
  return apiFileRequest(path(entity, id, format), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value),
  })
}
