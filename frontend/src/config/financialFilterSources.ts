import { apiRequest } from '../api/client'
import type { EntitySources } from '../filters/types'

type SearchResult = { results: Array<{ id: number; name: string; short_name: string }>; has_more: boolean }
function organizationSource(kind: 'institutions' | 'funders') {
  const request = (params: URLSearchParams, signal: AbortSignal) => apiRequest<SearchResult>(`/api/v1/financial/organizations/?${params}`, { signal })
  return {
    async search(search: string, signal: AbortSignal) {
      const data = await request(new URLSearchParams({ kind, search }), signal)
      return { options: data.results.map((item) => ({ value: String(item.id), label: `${item.short_name} · ${item.name}` })), hasMore: data.has_more }
    },
    async resolve(id: string, signal: AbortSignal) {
      const data = await request(new URLSearchParams({ kind, id }), signal)
      const item = data.results[0]
      return item ? { value: String(item.id), label: `${item.short_name} · ${item.name}` } : null
    },
  }
}
export const financialFilterSources = { financialInstitutions: organizationSource('institutions'), financialFunders: organizationSource('funders') } satisfies EntitySources
