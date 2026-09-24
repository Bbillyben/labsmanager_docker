import type { SupportedFilter } from '../filters/types'

export const projectFilters = [
  { id: 'active', label: 'Activité', category: 'Situation', type: 'static-choice', parameter: 'status', defaultValue: 'true', options: [{ value: 'true', label: 'Actifs' }, { value: 'false', label: 'Inactifs' }] },
  { id: 'stale', label: 'En retard', category: 'Situation', type: 'static-choice', parameter: 'stale', options: [{ value: 'true', label: 'Oui' }, { value: 'false', label: 'Non' }] },
  { id: 'projectName', label: 'Nom du projet', category: 'Projet', type: 'text', parameter: 'project_name' },
  { id: 'startDate', label: 'Date de début', category: 'Dates', type: 'date', parameter: 'start_date' },
  { id: 'endDate', label: 'Date de fin', category: 'Dates', type: 'date', parameter: 'end_date' },
  { id: 'participant', label: 'Participant', category: 'Relations', type: 'entity-search', parameter: 'participant', source: 'allEmployees', idFormat: 'positive-integer', placeholder: 'Nom ou prénom…' },
  { id: 'fundReference', label: 'Référence de fonds', category: 'Relations', type: 'text', parameter: 'fundref' },
  { id: 'funder', label: 'Financeur', category: 'Relations', type: 'dynamic-choice', parameter: 'funder', source: 'funders' },
  { id: 'institution', label: 'Institution', category: 'Relations', type: 'dynamic-choice', parameter: 'institution_name', source: 'institutions' },
  { id: 'team', label: 'Équipe', category: 'Relations', type: 'dynamic-choice', parameter: 'team', source: 'teams' },
] as const satisfies readonly SupportedFilter[]
