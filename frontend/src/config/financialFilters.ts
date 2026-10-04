import type { SupportedFilter } from '../filters/types'
import { translate, type I18nContextValue } from '../i18n/i18n'

export type FinancialKind = 'fund-items' | 'budgets' | 'expenses'
const bool = (t: I18nContextValue['t'], id: string, label: string, parameter: string) => ({ id, label, category: t('filters.categorySituation'), type: 'static-choice', parameter, options: [{ value: 'true', label: t('filters.yes') }, { value: 'false', label: t('filters.no') }] } as const)
const entity = (t: I18nContextValue['t'], id: string, label: string, source: string, parameter = id) => ({ id, label, category: t('filters.categoryRelations'), type: 'entity-search', parameter, source, idFormat: 'positive-integer' } as const)
const choice = (t: I18nContextValue['t'], id: string, label: string, source: string, parameter = id) => ({ id, label, category: t('filters.categoryRelations'), type: 'dynamic-choice', parameter, source } as const)
const text = (t: I18nContextValue['t'], id: string, label: string, parameter = id) => ({ id, label, category: t('filters.categoryRelations'), type: 'text', parameter } as const)
const amount = (t: I18nContextValue['t']) => ({ id: 'available', label: t('funding.available'), category: t('filters.categorySituation'), type: 'number', parameter: 'available' } as const)

export function financialFilters(kind: FinancialKind, t: I18nContextValue['t'] = (key, variables) => translate('fr', key, variables)): readonly SupportedFilter[] {
  const base = [entity(t, 'project', t('employee.project'), 'projects'), entity(t, 'institution', t('contracts.institution'), 'financialInstitutions'), entity(t, 'funder', t('contracts.funder'), 'financialFunders'), text(t, 'fundref', t('filters.fundReference'))]
  if (kind === 'fund-items') return [choice(t, 'type', t('funding.costType'), 'costTypes'), amount(t), bool(t, 'active', t('filters.activity'), 'active'), ...base, entity(t, 'participant', t('filters.participant'), 'allEmployees'), bool(t, 'stale', t('filters.overdue'), 'stale')]
  if (kind === 'budgets') return [bool(t, 'active', t('filters.activity'), 'active'), choice(t, 'type', t('funding.costType'), 'costTypes'), choice(t, 'contractType', t('contracts.contractType'), 'contractTypes', 'contract_type'), entity(t, 'employee', t('employee.identity'), 'allEmployees'), ...base, amount(t), choice(t, 'employeeType', t('projectBudgets.employeeType'), 'employeeTypes', 'emp_type')]
  return [choice(t, 'type', t('funding.costType'), 'costTypes'), { id: 'after', label: t('financial.after'), category: t('filters.categoryDates'), type: 'date', parameter: 'after' }, { id: 'before', label: t('financial.before'), category: t('filters.categoryDates'), type: 'date', parameter: 'before' }, text(t, 'desc', t('projectBudgets.description')), ...base, choice(t, 'status', t('expenses.status'), 'statuses'), text(t, 'expense_id', t('expenses.reference'))]
}
