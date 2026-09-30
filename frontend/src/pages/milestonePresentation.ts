import type { PlanningMilestoneState } from '../api/planning'
import type { TranslationKey } from '../i18n/i18n'

const stateKeys: Record<PlanningMilestoneState, TranslationKey> = {
  overdue: 'employee.stateOverdue',
  due_soon: 'employee.stateDueSoon',
  in_progress: 'employee.stateInProgress',
  planned: 'employee.statePlanned',
  completed: 'employee.stateCompleted',
}

export function milestoneStateKey(state: PlanningMilestoneState) {
  return stateKeys[state]
}
