import type { PlanningMilestoneState } from '../api/planning'
import type { TranslationKey } from '../i18n/i18n'

const stateKeys: Record<PlanningMilestoneState, TranslationKey> = {
  overdue: 'employee.stateOverdue',
  due_soon: 'employee.stateDueSoon',
  in_progress: 'employee.stateInProgress',
  planned: 'employee.statePlanned',
  completed: 'employee.stateCompleted',
}

/** Choose the display state for a milestone using its dates and status. */
export function milestoneStateKey(state: PlanningMilestoneState) {
  return stateKeys[state]
}
