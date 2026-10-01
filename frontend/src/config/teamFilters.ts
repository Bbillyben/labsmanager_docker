import type { SupportedFilter } from '../filters/types'
import { translate, type I18nContextValue } from '../i18n/i18n'

export const teamFilters = (t: I18nContextValue['t'] = (key, variables) => translate('fr', key, variables)) => [
  { id: 'name', label: t('team.name'), category: t('filters.categoryProject'), type: 'text', parameter: 'name' },
  { id: 'leader', label: t('team.leader'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'leader', source: 'allEmployees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder') },
  { id: 'mate', label: t('team.members'), category: t('filters.categoryRelations'), type: 'entity-search', parameter: 'mate', source: 'allEmployees', idFormat: 'positive-integer', placeholder: t('filters.personPlaceholder') },
] as const satisfies readonly SupportedFilter[]
