import { apiRequest } from './client'

export type ChartEmployee = {
  id: number
  name: string
  is_active: boolean
  statuses: { code: string; name: string }[]
  can_view: boolean
}

export type ChartRelationship = { superior_id: number; employee_id: number }
export type OrganizationChart = {
  show_current_only: boolean
  employees: ChartEmployee[]
  relationships: ChartRelationship[]
}

const url = '/api/v1/organization-chart/'

export function getOrganizationChart(signal?: AbortSignal) {
  return apiRequest<OrganizationChart>(url, { signal })
}

export function setOrganizationChartScope(showCurrentOnly: boolean) {
  return apiRequest<{ show_current_only: boolean }>(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ show_current_only: showCurrentOnly }),
  })
}
