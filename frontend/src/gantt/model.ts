export type GanttIdentity = { kind: 'project' | 'participation' | 'work' | 'calendar'; id: string }

export type LabsManagerGanttItem = {
  key: string
  parentKey?: string
  kind: 'group' | 'participation' | 'task' | 'milestone'
  label: string
  start: string | null
  end: string | null
  state?: 'overdue' | 'due_soon' | 'completed' | 'planned' | 'in_progress'
  identity: GanttIdentity
}

export type LabsManagerGanttDependency = {
  id: string
  predecessor: GanttIdentity
  successor: GanttIdentity
  temporallyInconsistent: boolean
}

export type LabsManagerGanttData = { items: LabsManagerGanttItem[]; dependencies: LabsManagerGanttDependency[] }
