export type FilterOption = { value: string; label: string }
export type EntitySearchSource = {
  search: (query: string, signal: AbortSignal) => Promise<{ options: FilterOption[]; hasMore: boolean }>
  resolve: (id: string, signal: AbortSignal) => Promise<FilterOption | null>
}
export type ChoiceSource = {
  loadAll: (signal: AbortSignal) => Promise<FilterOption[]>
}
export type EntitySources = Readonly<Record<string, EntitySearchSource>>

type Base = { id: string; label: string; category: string; description?: string; placeholder?: string }
type Single = { multiple?: false; serialization?: never }
type Multiple = { multiple: true; serialization: 'csv' | 'repeat' }
export type StaticChoiceFilter = Base & Single & {
  type: 'static-choice'; parameter: string; options: readonly FilterOption[]
}
export type EntityFilter = Base & Single & {
  type: 'entity-search'; parameter: string; source: string; idFormat?: 'positive-integer'
}
// Only these controls are renderable today. Future definitions cannot accidentally
// enter a live catalogue before their controls and server contracts are supplied.
export type SupportedFilter = StaticChoiceFilter | EntityFilter
export type DynamicChoiceFilter = Base & (Single | Multiple) & {
  type: 'dynamic-choice'; parameter: string; source: string
}
export type RangeValue = { lower?: string; upper?: string }
export type RangeFilter = Base & {
  type: 'range'; valueType: 'date' | 'number'; parameters: { lower: string; upper: string }
}
export type FilterDefinition = SupportedFilter | DynamicChoiceFilter | RangeFilter | (Base & {
  type: 'date' | 'text' | 'number'; parameter: string
})
