export class ApiError extends Error {
  readonly status: number
  readonly payload: unknown

  constructor(status: number, payload: unknown) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export type MutationError = {
  kind: 'validation' | 'forbidden' | 'notFound' | 'unauthorized' | 'server' | 'network'
  fields: Record<string, string[]>
  messages: string[]
}

/** Preserve DRF messages as text; callers translate only transport fallbacks. */
export function normalizeMutationError(error: unknown): MutationError {
  const result: MutationError = { kind: 'network', fields: {}, messages: [] }
  if (!(error instanceof ApiError)) return result
  result.kind = error.status === 400 ? 'validation' : error.status === 403 ? 'forbidden'
    : error.status === 404 ? 'notFound' : error.status === 401 ? 'unauthorized' : 'server'
  const strings = (value: unknown): string[] => typeof value === 'string' ? [value]
    : Array.isArray(value) ? value.flatMap(strings) : []
  if (error.payload && typeof error.payload === 'object' && !Array.isArray(error.payload)) {
    for (const [key, value] of Object.entries(error.payload)) {
      if (key === 'non_field_errors' || key === 'detail') result.messages.push(...strings(value))
      else result.fields[key] = strings(value)
    }
  } else result.messages.push(...strings(error.payload))
  return result
}
