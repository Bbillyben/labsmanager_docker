import type { EmployeeMilestoneState } from '../api/employees'
import type { TranslationKey } from '../i18n/i18n'

const stateKeys: Record<EmployeeMilestoneState, TranslationKey> = {
  overdue: 'employee.stateOverdue',
  due_soon: 'employee.stateDueSoon',
  in_progress: 'employee.stateInProgress',
  planned: 'employee.statePlanned',
  completed: 'employee.stateCompleted',
}

export function milestoneStateKey(state: EmployeeMilestoneState) {
  return stateKeys[state]
}
