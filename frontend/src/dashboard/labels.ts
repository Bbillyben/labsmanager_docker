import type { useTranslation } from '../i18n/i18n'

type Translate = ReturnType<typeof useTranslation>['t']
export function dashboardRendererLabel(key: string, fallback: string, t: Translate) {
  switch (key) {
    case 'kpi': return t('dashboard.renderer.kpi')
    case 'compact-list': return t('dashboard.renderer.compact-list')
    case 'alert-list': return t('dashboard.renderer.alert-list')
    case 'progress-list': return t('dashboard.renderer.progress-list')
    case 'overview-list': return t('dashboard.renderer.overview-list')
    case 'deadline-list': return t('dashboard.renderer.deadline-list')
    case 'contract-list': return t('dashboard.renderer.contract-list')
    case 'employee-movements': return t('dashboard.renderer.employee-movements')
    case 'task-workload': return t('dashboard.renderer.task-workload')
    case 'timeline-calendar': return t('dashboard.renderer.timeline-calendar')
    case 'calendar-grid': return t('dashboard.renderer.calendar-grid')
    case 'project-portfolio': return t('dashboard.renderer.project-portfolio')
    case 'employee-workload': return t('dashboard.renderer.employee-workload')
    case 'empty': return t('dashboard.renderer.empty')
    case 'line-chart': return t('dashboard.renderer.line-chart')
    case 'data-consistency': return t('dashboard.renderer.data-consistency')
    default: return fallback
  }
}
export function dashboardFieldLabel(key: string, fallback: string, t: Translate, sourceKey = '') {
  if (sourceKey === 'core.timeline' && key.startsWith('tasks_')) return dashboardFieldLabel(key.slice(6), fallback, t, 'core.tasks')
  if (sourceKey === 'core.timeline' && key.startsWith('milestones_')) return dashboardFieldLabel(key.slice(11), fallback, t, 'core.milestones')
  switch (key) {
    case 'include_tasks': return t('dashboard.timeline.includeTasks')
    case 'include_milestones': return t('dashboard.timeline.includeMilestones')
    case 'calendar_days': return t('dashboard.timeline.horizon')
    case 'employee_id': return t('dashboard.workload.employee')
    case 'team_id': return t('dashboard.workload.team')
    case 'metric': return t('dashboard.workload.metricLabel')
    case 'message': return t('dashboard.field.message')
    case 'active_only': return sourceKey === 'core.contracts' ? t('dashboard.field.active_contracts') :
      sourceKey === 'core.funds' ? t('dashboard.field.active_funds') :
      sourceKey === 'core.employees' ? t('dashboard.field.active_employees') : t('dashboard.field.active_only')
    case 'limit': return t('dashboard.field.limit')
    case 'scope': return t('dashboard.field.scope')
    case 'project_scope': return t('dashboard.field.project_scope')
    case 'project_id': return t('dashboard.field.project_id')
    case 'display': return t('dashboard.field.display')
    case 'group_by': return t('dashboard.field.group_by')
    case 'months': return t('dashboard.field.months')
    case 'late_only': return t('dashboard.field.late_only')
    case 'status': return t('dashboard.field.status')
    case 'overdue_only': return t('dashboard.field.overdue_only')
    case 'due_within_days': return t('dashboard.field.due_within_days')
    case 'ending_within_days': return t('dashboard.field.ending_within_days')
    case 'current_only': return t('dashboard.field.current_only')
    case 'stale_only': return t('dashboard.field.stale_only')
    case 'movement': return t('dashboard.field.movement')
    case 'within_days': return t('dashboard.field.within_days')
    case 'upcoming_days': return t('dashboard.field.upcoming_days')
    default: return fallback
  }
}
export function dashboardChoiceLabel(value: string, t: Translate) {
  switch (value) {
    case 'all_visible': return t('dashboard.choice.all_visible')
    case 'context': return t('dashboard.choice.context')
    case 'specific_project': return t('dashboard.choice.specific_project')
    case 'cumulative': return t('dashboard.choice.cumulative')
    case 'period': return t('dashboard.choice.period')
    case 'total': return t('dashboard.choice.total')
    case 'fund': return t('dashboard.choice.fund')
    case 'cost_type': return t('dashboard.choice.cost_type')
    case 'institution': return t('dashboard.choice.institution')
    case 'participated': return t('dashboard.choice.participated')
    case 'managed': case 'managed_projects': return t('dashboard.choice.managed')
    case 'mine': case 'self': return t('dashboard.choice.mine')
    case 'subordinates': return t('dashboard.choice.subordinates')
    case 'single': return t('dashboard.workload.scope.single')
    case 'team': return t('dashboard.workload.scope.team')
    case 'project_allocation': return t('dashboard.workload.metric.project_allocation')
    case 'open_tasks': return t('dashboard.workload.metric.open_tasks')
    case 'open_milestones': return t('dashboard.workload.metric.open_milestones')
    case 'open_work_items': return t('dashboard.workload.metric.open_work_items')
    case 'all': return t('dashboard.choice.all')
    case 'open': return t('dashboard.choice.open')
    case 'done': return t('dashboard.choice.done')
    case 'arrivals': return t('dashboard.choice.arrivals')
    case 'departures': return t('dashboard.choice.departures')
    case '0': return t('dashboard.choice.anyTime')
    case '7': case '14': case '21': case '30': case '60': case '90': return t('dashboard.choice.days', { days: value })
    default: return value
  }
}
export function dashboardSourceLabel(key: string, fallback: string, t: Translate) {
  switch (key) {
    case 'core.links': return t('dashboard.quickLinks')
    case 'core.note': return t('dashboard.note')
    case 'core.projects': return t('dashboard.visibleProjects')
    case 'core.milestones': return t('dashboard.source.milestones')
    case 'core.funds': return t('dashboard.source.funds')
    case 'core.contracts': return t('dashboard.source.contracts')
    case 'core.employees': return t('dashboard.source.employees')
    case 'core.leaves': return t('dashboard.source.leaves')
    case 'core.tasks': return t('dashboard.source.tasks')
    case 'core.timeline': return t('dashboard.source.timeline')
    case 'core.employee-workload': return t('dashboard.source.employeeWorkload')
    case 'core.financial-advancement': return t('dashboard.source.advancement')
    case 'core.financial-summary': return t('dashboard.source.financialSummary')
    case 'core.expense-trend': return t('dashboard.source.expenseTrend')
    case 'core.data-consistency': return t('dataConsistency.title')
    default: return fallback
  }
}
export function dashboardSourceDescription(key: string, fallback: string, t: Translate) {
  switch (key) {
    case 'core.links': return t('dashboard.sourceDescription.links')
    case 'core.note': return t('dashboard.sourceDescription.note')
    case 'core.projects': return t('dashboard.sourceDescription.projects')
    case 'core.milestones': return t('dashboard.sourceDescription.milestones')
    case 'core.funds': return t('dashboard.sourceDescription.funds')
    case 'core.contracts': return t('dashboard.sourceDescription.contracts')
    case 'core.employees': return t('dashboard.sourceDescription.employees')
    case 'core.leaves': return t('dashboard.sourceDescription.leaves')
    case 'core.tasks': return t('dashboard.sourceDescription.tasks')
    case 'core.timeline': return t('dashboard.sourceDescription.timeline')
    case 'core.employee-workload': return t('dashboard.sourceDescription.employeeWorkload')
    case 'core.financial-advancement': return t('dashboard.sourceDescription.advancement')
    case 'core.financial-summary': return t('dashboard.sourceDescription.financialSummary')
    case 'core.expense-trend': return t('dashboard.sourceDescription.expenseTrend')
    case 'core.data-consistency': return t('dashboard.sourceDescription.dataConsistency')
    default: return fallback
  }
}
export function dashboardCategoryLabel(key: string, t: Translate) {
  switch (key) {
    case 'General': return t('dashboard.category.general')
    case 'Projects': return t('dashboard.category.projects')
    case 'Finance': return t('dashboard.category.finance')
    case 'Administration': return t('dashboard.category.administration')
    case 'HR': return t('dashboard.category.hr')
    case 'Work': return t('dashboard.category.work')
    default: return key
  }
}
