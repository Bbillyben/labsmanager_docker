import type { SupportedFilter } from './types'

/** An empty parameter persists an added control without applying a server filter. */
export function readFilterQuery(catalogue: readonly SupportedFilter[], query: URLSearchParams) {
  const result = new URLSearchParams()
  for (const filter of catalogue) {
    const value = query.get(filter.parameter)
    if (value === null) continue
    if (value !== '') {
      if (filter.type === 'static-choice' && !filter.options.some((option) => option.value === value)) continue
      if (filter.type === 'entity-search' && filter.idFormat === 'positive-integer' && !/^[1-9]\d*$/.test(value)) continue
    }
    result.set(filter.parameter, value)
  }
  return result
}

export function changeFilter(query: URLSearchParams, filter: SupportedFilter, value: string | null, resetParameters: readonly string[] = []) {
  const next = new URLSearchParams(query)
  if (value === null) next.delete(filter.parameter)
  else next.set(filter.parameter, value)
  resetParameters.forEach((parameter) => next.delete(parameter))
  return next
}

export function resetFilters(query: URLSearchParams, catalogue: readonly SupportedFilter[], resetParameters: readonly string[] = []) {
  const next = new URLSearchParams(query)
  catalogue.forEach((filter) => next.delete(filter.parameter))
  resetParameters.forEach((parameter) => next.delete(parameter))
  return next
}
