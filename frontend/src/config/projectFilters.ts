import type { SupportedFilter } from '../filters/types'
import { translate, type I18nContextValue } from '../i18n/i18n'

export const projectFilters = (t: I18nContextValue['t'] = (key, variables) => translate('fr', key, variables)) => [
  { id: 'active', label: t('filters.activity'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'status', defaultValue: 'true', options: [{ value: 'true', label: t('filters.active') }, { value: 'false', label: t('filters.inactive') }] },
  { id: 'stale', label: t('filters.overdue'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'stale', options: [{ value: 'true', label: t('filters.yes') }, { value: 'false', label: t('filters.no') }] },
  { id: 'projectName', label: t('filters.projectName'), category: t('filters.categoryProject'), type: 'text', parameter: 'project_name' },
  { id: 'startDate', label: t('filters.startDate'), category: t('filters.categoryDates'), type: 'date', parameter: 'start_date' },
  { id: 'endDate', label: t('filters.endDate'), category: t('filters.categoryDates'), type: 'date', parameter: 'end_date' },
  { id: 'participant', label: t('filters.participant'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'participant', source: 'allEmployees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder') },
  { id: 'fundReference', label: t('filters.fundReference'), category: t('filters.categoryRelations'), type: 'text', parameter: 'fundref' },
  { id: 'funder', label: t('filters.funder'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'funder', source: 'funders' },
  { id: 'institution', label: t('filters.institution'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'institution_name', source: 'institutions' },
  { id: 'team', label: t('filters.team'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'team', source: 'teams' },
] as const satisfies readonly SupportedFilter[]
