import type { PlanningMilestone } from '../api/planning'
import type { LabsManagerGanttData, LabsManagerGanttItem } from './model'

type PlanningParticipationRow = {
  id: number
  project: { id: number; name: string; start_date?: string | null; end_date?: string | null }
  role: { label: string }
  start_date: string | null
  end_date: string | null
}

export function adaptPlanningGantt(work: PlanningMilestone[], participations: PlanningParticipationRow[] = [], projects: Array<{ id: number; name: string; start_date?: string | null; end_date?: string | null }> = []): LabsManagerGanttData {
  const groups = new Map<number, LabsManagerGanttItem>()
  const children = new Map<number, LabsManagerGanttItem[]>()
  const ensure = (project: { id: number; name: string; start_date?: string | null; end_date?: string | null }) => {
    if (!groups.has(project.id)) groups.set(project.id, {
      key: `project:${project.id}`, kind: 'group', label: project.name,
      start: project.start_date ?? null, end: project.end_date ?? null,
      identity: { kind: 'project', id: String(project.id) },
    })
    if (!children.has(project.id)) children.set(project.id, [])
  }
  projects.forEach(ensure)
  for (const participation of participations) {
    ensure(participation.project)
    children.get(participation.project.id)!.push({
      key: `participation:${participation.id}`, parentKey: `project:${participation.project.id}`,
      kind: 'participation', label: participation.role.label,
      start: participation.start_date, end: participation.end_date,
      identity: { kind: 'participation', id: String(participation.id) },
    })
  }
  for (const item of work) {
    ensure(item.project)
    children.get(item.project.id)!.push({
      key: `work:${item.id}`, parentKey: `project:${item.project.id}`,
      kind: item.work_kind, label: item.name,
      start: item.start_date, end: item.end_date, state: item.display_state,
      identity: { kind: 'work', id: String(item.id) },
    })
  }
  return {
    items: [...groups.values()].flatMap((group) => [group, ...(children.get(Number(group.identity.id)) ?? [])]),
    dependencies: work.flatMap((item) => (item.dependencies ?? []).map((dependency) => ({
      id: String(dependency.id),
      predecessor: { kind: 'work' as const, id: String(dependency.predecessor_id) },
      successor: { kind: 'work' as const, id: String(dependency.successor_id) },
      temporallyInconsistent: dependency.temporally_inconsistent,
    }))),
  }
}
