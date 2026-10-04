import { useEffect, useState } from 'react'
import { getSearchSchema, search, type SearchProviderSchema, type SearchResult } from '../api/globalSearch'
import { ApiError } from '../api/errors'

export type SearchError = { message: string; position: number | null } | null

function syntaxError(error: unknown): SearchError {
  if (!(error instanceof ApiError) || error.status !== 400 || !error.payload || typeof error.payload !== 'object') return null
  const payload = error.payload as Record<string, unknown>
  return payload.error === 'invalid_search_query' && typeof payload.message === 'string'
    ? { message: payload.message, position: typeof payload.position === 'number' ? payload.position : null } : null
}

export function useSearchSchema() {
  const [providers, setProviders] = useState<SearchProviderSchema[]>([])
  useEffect(() => {
    const controller = new AbortController()
    void getSearchSchema(controller.signal).then((response) => setProviders(Array.isArray(response.providers) ? response.providers : [])).catch(() => {})
    return () => controller.abort()
  }, [])
  return providers
}

export function useGlobalSearch(query: string, options: { provider?: string; limit: number; perProvider: number; delay?: number }) {
  const { provider, limit, perProvider, delay = 250 } = options
  const [response, setResponse] = useState<{ key: string; results: SearchResult[]; counts: Record<string, number> }>({ key: '', results: [], counts: {} })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<{ key: string; value: 'generic' | Exclude<SearchError, null> } | null>(null)
  const requestKey = `${provider ?? ''}\u0000${query}`

  useEffect(() => {
    if (query.trim().length < 2) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setLoading(true)
      void search(query, { provider, limit, perProvider, signal: controller.signal })
        .then((data) => { if (!controller.signal.aborted) { setResponse({ key: requestKey, results: data.results, counts: data.counts ?? {} }); setError(null); setLoading(false) } })
        .catch((cause: unknown) => { if (!controller.signal.aborted) { setError({ key: requestKey, value: syntaxError(cause) ?? 'generic' }); setLoading(false) } })
    }, delay)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query, provider, limit, perProvider, delay, requestKey])

  const ready = query.trim().length >= 2
  return { results: ready && response.key === requestKey ? response.results : [],
           counts: ready && response.key === requestKey ? response.counts : {},
           loading: ready && loading, error: ready && error?.key === requestKey ? error.value : null }
}
