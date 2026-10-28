declare module '@labsmanager/plugin-ui' {
  import type { ComponentType } from 'react'

  export const PLUGIN_UI_API_VERSION: 1
  export const EntitySearch: ComponentType<{
    id: string; label: string; value: string; onChange: (value: string) => void
    source: { search: (query: string, signal: AbortSignal) => Promise<{
      options: Array<{ value: string; label: string }>; hasMore: boolean
    }>; resolve: (id: string, signal: AbortSignal) => Promise<{ value: string; label: string } | null> }
  }>
  export const employeeFilterSources: { employees: React.ComponentProps<typeof EntitySearch>['source'] }
  export function useTranslation(): { t: (key: string) => string }
}
