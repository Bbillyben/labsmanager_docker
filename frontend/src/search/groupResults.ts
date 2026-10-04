import type { SearchProviderSchema, SearchResult } from '../api/globalSearch'

export function groupResults(results: SearchResult[], providers: SearchProviderSchema[]) {
  const groups = new Map<string, SearchResult[]>()
  for (const result of results) groups.set(result.provider_key, [...(groups.get(result.provider_key) ?? []), result])
  const order = new Map(providers.map((provider, index) => [provider.key, index]))
  return [...groups].sort(([left], [right]) => (order.get(left) ?? Infinity) - (order.get(right) ?? Infinity))
}

export function providerLabel(key: string, providers: SearchProviderSchema[]) {
  return providers.find((provider) => provider.key === key)?.label ?? key
}
