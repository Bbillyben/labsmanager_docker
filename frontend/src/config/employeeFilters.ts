import type { SupportedFilter } from '../filters/types'

export const employeeFilters = [
  {
    id: 'activity', label: 'Activité', category: 'Situation', description: 'Actif ou inactif',
    type: 'static-choice', parameter: 'is_active', multiple: false,
    options: [{ value: 'true', label: 'Actifs' }, { value: 'false', label: 'Inactifs' }],
  },
  {
    id: 'superior', label: 'Supérieur', category: 'Relations', description: 'Responsable actuel',
    type: 'entity-search', parameter: 'superior', multiple: false,
    source: 'employees', idFormat: 'positive-integer', placeholder: 'Nom ou prénom…',
  },
] as const satisfies readonly SupportedFilter[]
