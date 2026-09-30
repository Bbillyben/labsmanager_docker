import type { EmployeeProjectParticipation } from '../api/employees'
import type { PlanningMilestone } from '../api/planning'
import { adaptPlanningGantt } from './PlanningGanttAdapter'

/** Keep Employee participation rows while sharing Planning adaptation across scopes. */
export function adaptEmployeeGantt(participations: EmployeeProjectParticipation[], work: PlanningMilestone[]) {
  return adaptPlanningGantt(work, participations)
}
