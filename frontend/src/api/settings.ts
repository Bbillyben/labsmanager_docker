import { apiRequest } from './client'

export type SettingChoice = { value: string; label: string }
export type SettingValue = boolean | string | number
export type SettingData = {
  key: string
  name: string
  description: string
  type: 'boolean' | 'choice' | 'integer' | 'decimal' | 'string' | 'color' | 'related field'
  value: SettingValue
  default: SettingValue
  choices: SettingChoice[]
}

const projectPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/settings/`

export function getProjectSettings(projectId: string, signal: AbortSignal) {
  return apiRequest<{ settings: SettingData[] }>(projectPath(projectId), { signal })
}

export function updateProjectSetting(projectId: string, key: string, value: SettingValue) {
  return apiRequest<SettingData>(`${projectPath(projectId)}${encodeURIComponent(key)}/`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }),
  })
}
