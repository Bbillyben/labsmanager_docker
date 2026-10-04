import { apiRequest } from './client'

export type SearchResult = {
  provider_key: string
  object_id: string
  title: string
  subtitle: string
  url: string
  score: number
  icon: string
  match_reason: string
  metadata: Record<string, unknown>
}

export type SearchProviderSchema = {
  key: string
  label: string
  icon: string
  fields: { key: string; label: string; type: string; operators: string[]; suggest_values: boolean }[]
  supports_generic_info: boolean
  autocomplete: boolean
}

export type SearchSchema = { providers: SearchProviderSchema[] }
export type SearchSuggestion = { kind: 'provider' | 'field' | 'operator' | 'generic_info_type' | 'value'; label: string; insert_text: string; detail: string }
export type SearchAutocomplete = { context: string; replace_start: number; replace_end: number; suggestions: SearchSuggestion[]; incomplete: boolean }
export type SearchResponse = { query: string; results: SearchResult[]; groups: Record<string, number>; counts: Record<string, number> }
export type SearchOptions = { provider?: string; limit?: number; perProvider?: number; signal?: AbortSignal }

export function search(query: string, { provider, limit, perProvider, signal }: SearchOptions = {}) {
  const params = new URLSearchParams({ q: query })
  if (provider) params.set('provider', provider)
  if (limit !== undefined) params.set('limit', String(limit))
  if (perProvider !== undefined) params.set('per_provider', String(perProvider))
  return apiRequest<SearchResponse>(`/api/v1/search/?${params}`, { signal })
}

export function getSearchSchema(signal?: AbortSignal) {
  return apiRequest<SearchSchema>('/api/v1/search/schema/', { signal })
}

export function getSearchAutocomplete(query: string, cursor: number, { provider, signal }: { provider?: string; signal?: AbortSignal } = {}) {
  const params = new URLSearchParams({ q: query, cursor: String(cursor) })
  if (provider) params.set('provider', provider)
  return apiRequest<SearchAutocomplete>(`/api/v1/search/autocomplete/?${params}`, { signal })
}
