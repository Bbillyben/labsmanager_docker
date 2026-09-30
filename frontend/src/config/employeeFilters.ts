import type { SupportedFilter } from '../filters/types'
import { translate, type I18nContextValue } from '../i18n/i18n'

export const employeeFilters = (t: I18nContextValue['t'] = (key, variables) => translate('fr', key, variables)) => [
  {
    id: 'activity', label: t('filters.activity'), category: t('filters.categorySituation'), description: t('filters.activeDescription'),
    type: 'static-choice', parameter: 'is_active', multiple: false, defaultValue: 'true',
    options: [{ value: 'true', label: t('filters.active') }, { value: 'false', label: t('filters.inactive') }],
  },
  { id: 'name', label: t('filters.employeeName'), category: t('filters.categoryIdentity'), type: 'text', parameter: 'search' },
  {
    id: 'superior', label: t('filters.superior'), category: t('filters.categoryRelations'), description: t('filters.currentManager'),
    type: 'entity-search', parameter: 'superior', multiple: false,
    source: 'employees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder'),
  },
  { id: 'status', label: t('filters.status'), category: t('filters.categorySituation'), type: 'dynamic-choice', parameter: 'status', source: 'statuses' },
  { id: 'currentStatus', label: t('filters.currentStatus'), category: t('filters.categorySituation'), type: 'dynamic-choice', parameter: 'current_status', source: 'statuses' },
  { id: 'team', label: t('filters.team'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'team', source: 'teams' },
  { id: 'project', label: t('filters.project'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'project', source: 'projects', idFormat: 'positive-integer', placeholder: t('filters.projectPlaceholder') },
] as const satisfies readonly SupportedFilter[]
