import type { ChartEmployee, ChartRelationship } from '../api/organizationChart'

export type OrganizationGraph = {
  employees: ChartEmployee[]
  relationships: ChartRelationship[]
  roots: number[]
  matches: Set<number>
  ancestors: Set<number>
  descendants: Set<number>
  highlighted: Set<number>
  expandable: Set<number>
  isolated: Set<number>
}

export type OrganizationHighlight = 'match' | 'ancestor' | 'descendant' | 'none'

export function organizationHighlight(graph: OrganizationGraph, id: number): OrganizationHighlight {
  if (graph.matches.has(id)) return 'match'
  if (graph.ancestors.has(id)) return 'ancestor'
  if (graph.descendants.has(id)) return 'descendant'
  return 'none'
}

/** Derive visible nodes from active edges, so a second superior keeps a child visible. */
export function buildOrganizationGraph(
  employees: ChartEmployee[],
  relationships: ChartRelationship[],
  collapsed: ReadonlySet<number>,
  search: string,
): OrganizationGraph {
  const employeeIds = new Set(employees.map((employee) => employee.id))
  const edges = relationships.filter((edge) => employeeIds.has(edge.superior_id) && employeeIds.has(edge.employee_id))
  const parents = new Map<number, number[]>()
  const children = new Map<number, number[]>()
  for (const edge of edges) {
    if (!parents.has(edge.employee_id)) parents.set(edge.employee_id, [])
    if (!children.has(edge.superior_id)) children.set(edge.superior_id, [])
    parents.get(edge.employee_id)!.push(edge.superior_id)
    children.get(edge.superior_id)!.push(edge.employee_id)
  }
  const roots = employees.filter((employee) => !parents.has(employee.id)).map((employee) => employee.id)
  // Classification uses the selected business graph, before display-only collapse.
  const isolated = new Set(roots.filter((id) => !children.has(id)))
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const matches = new Set(normalizedSearch
    ? employees.filter((employee) => employee.name.toLocaleLowerCase().includes(normalizedSearch)).map((employee) => employee.id)
    : [])
  const ancestors = new Set<number>()
  const ancestorQueue = [...matches]
  for (let cursor = 0; cursor < ancestorQueue.length; cursor += 1) {
    for (const parent of parents.get(ancestorQueue[cursor]) ?? []) {
      if (!ancestors.has(parent)) { ancestors.add(parent); ancestorQueue.push(parent) }
    }
  }
  const descendants = new Set<number>()
  const descendantQueue = [...matches]
  for (let cursor = 0; cursor < descendantQueue.length; cursor += 1) {
    for (const child of children.get(descendantQueue[cursor]) ?? []) {
      if (!descendants.has(child)) { descendants.add(child); descendantQueue.push(child) }
    }
  }
  const highlighted = new Set([...matches, ...ancestors, ...descendants])
  const searchPaths = new Set([...matches, ...ancestors])
  const visible = new Set<number>()
  const queue = [...roots]
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const id = queue[cursor]
    if (visible.has(id)) continue
    visible.add(id)
    if (!collapsed.has(id)) queue.push(...(children.get(id) ?? []))
    else if (normalizedSearch && searchPaths.has(id)) queue.push(...(children.get(id) ?? []).filter((child) => searchPaths.has(child)))
  }
  return {
    employees: employees.filter((employee) => visible.has(employee.id)),
    relationships: edges.filter((edge) => visible.has(edge.superior_id) && visible.has(edge.employee_id)
      && (!collapsed.has(edge.superior_id) || (normalizedSearch !== '' && searchPaths.has(edge.superior_id) && searchPaths.has(edge.employee_id)))),
    roots,
    matches,
    ancestors,
    descendants,
    highlighted,
    expandable: new Set(children.keys()),
    isolated,
  }
}
