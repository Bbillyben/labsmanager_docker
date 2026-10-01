import type { SupportedFilter } from '../filters/types'
import { translate, type I18nContextValue } from '../i18n/i18n'

export const contractFilters = (t: I18nContextValue['t'] = (key, variables) => translate('fr', key, variables)) => [
  { id: 'active', label: t('contractHub.active'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'active', options: [{ value: 'true', label: t('filters.yes') }, { value: 'false', label: t('filters.no') }] },
  { id: 'ongoing', label: t('contractHub.ongoing'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'ongoing', options: [{ value: 'true', label: t('filters.yes') }, { value: 'false', label: t('filters.no') }] },
  { id: 'stale', label: t('contractHub.stale'), category: t('filters.categorySituation'), type: 'static-choice', parameter: 'stale', options: [{ value: 'true', label: t('filters.yes') }, { value: 'false', label: t('filters.no') }] },
  { id: 'employee', label: t('employee.identity'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'employee', source: 'allEmployees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder') },
  { id: 'contractType', label: t('contracts.contractType'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'type', source: 'contractTypes' },
  { id: 'contractStatus', label: t('contractHub.status'), category: t('filters.categorySituation'), type: 'dynamic-choice', parameter: 'cont_status', source: 'contractStatuses' },
  { id: 'project', label: t('employee.project'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'project', source: 'projects', idFormat: 'positive-integer' },
  { id: 'funder', label: t('contracts.funder'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'funder', source: 'funders' },
  { id: 'institution', label: t('contracts.institution'), category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter: 'institution', source: 'institutions' },
] as const satisfies readonly SupportedFilter[]
