import { apiRequest } from './client'

export type SystemInfo = {
  system_info: Record<string, string | number | boolean | null>
  help_links: { label: string; url: string }[]
}

export const getSystemInfo = (signal?: AbortSignal) =>
  apiRequest<SystemInfo>('/api/v1/system-info/', { signal })


export const formatSystemValue = (key: string, value: unknown): string => {
  if (value === null || value === undefined) {
    return ''
  }

  if (key === 'database' && typeof value === 'object' && !Array.isArray(value)) {
    const database = value as { vendor?: string; version?: string | null }

    return [database.vendor, database.version]
      .filter(Boolean)
      .join(' ')
  }

  if (key === 'plugins' && Array.isArray(value)) {
    return value
      .map((plugin) => {
        if (typeof plugin !== 'object' || plugin === null) {
          return String(plugin)
        }

        const p = plugin as {
          name?: string
          slug?: string
          active?: boolean
          mixins?: string[]
        }

        const name = p.name ?? p.slug ?? 'unknown'
        const state = p.active ? 'active' : 'inactive'
        const mixins = p.mixins?.length
          ? ` [${p.mixins.join(', ')}]`
          : ''

        return `${name} (${state})${mixins}`
      })
      .join('; ')
  }

  if (Array.isArray(value) || typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}