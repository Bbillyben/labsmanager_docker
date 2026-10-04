import ELK from 'elkjs/lib/elk.bundled.js'
import type { Edge, Node } from '@xyflow/react'
import type { OrganizationGraph } from './organizationGraph'

export const NODE_WIDTH = 220
export const NODE_HEIGHT = 88
const COLUMN_GAP = 36
const ROW_GAP = 44
const ISOLATED_GAP = 120
const elk = new ELK()

/** ELK arranges the first two levels; deeper DAG nodes share compact columns. */
export async function layoutOrganizationGraph(graph: OrganizationGraph): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const hierarchy = graph.employees.filter((employee) => !graph.isolated.has(employee.id))
  const isolated = graph.employees.filter((employee) => graph.isolated.has(employee.id))
  const hierarchyIds = new Set(hierarchy.map((employee) => employee.id))
  const parents = new Map<number, number[]>()
  const children = new Map<number, number[]>()
  const remainingParents = new Map(hierarchy.map((employee) => [employee.id, 0]))
  for (const edge of graph.relationships) {
    if (!hierarchyIds.has(edge.superior_id) || !hierarchyIds.has(edge.employee_id)) continue
    if (!parents.has(edge.employee_id)) parents.set(edge.employee_id, [])
    if (!children.has(edge.superior_id)) children.set(edge.superior_id, [])
    parents.get(edge.employee_id)!.push(edge.superior_id)
    children.get(edge.superior_id)!.push(edge.employee_id)
    remainingParents.set(edge.employee_id, remainingParents.get(edge.employee_id)! + 1)
  }

  const depth = new Map<number, number>()
  const anchors = new Map<number, Set<number>>()
  const order: number[] = []
  const queue = hierarchy.filter((employee) => remainingParents.get(employee.id) === 0).map((employee) => employee.id)
  for (const id of queue) depth.set(id, 0)
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const id = queue[cursor]
    order.push(id)
    const level = depth.get(id) ?? 0
    anchors.set(id, level === 1 ? new Set([id]) : new Set((parents.get(id) ?? []).flatMap((parent) => [...(anchors.get(parent) ?? [])])))
    for (const child of children.get(id) ?? []) {
      depth.set(child, Math.max(depth.get(child) ?? 0, level + 1))
      remainingParents.set(child, remainingParents.get(child)! - 1)
      if (remainingParents.get(child) === 0) queue.push(child)
    }
  }

  const upper = hierarchy.filter((employee) => (depth.get(employee.id) ?? 0) <= 1)
  const upperIds = new Set(upper.map((employee) => employee.id))
  const upperEdges = graph.relationships.filter((edge) => upperIds.has(edge.superior_id) && upperIds.has(edge.employee_id))
  const result = upper.length ? await elk.layout({
    id: 'organization',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.spacing.nodeNode': String(COLUMN_GAP),
      'elk.layered.spacing.nodeNodeBetweenLayers': '72',
      'elk.spacing.componentComponent': '80',
      'elk.layered.compaction.postCompaction.strategy': 'EDGE_LENGTH',
    },
    children: upper.map((employee) => ({ id: String(employee.id), width: NODE_WIDTH, height: NODE_HEIGHT })),
    edges: upperEdges.map((edge) => ({
      id: `${edge.superior_id}-${edge.employee_id}`,
      sources: [String(edge.superior_id)],
      targets: [String(edge.employee_id)],
    })),
  }) : null
  const positions = new Map<number, { x: number; y: number }>(result?.children?.map((node) => [Number(node.id), { x: node.x ?? 0, y: node.y ?? 0 }]) ?? [])
  const upperBottom = Math.max(0, ...[...positions.values()].map((point) => point.y + NODE_HEIGHT))
  const columnBottom = new Map<number, number>()
  for (const id of order) {
    if ((depth.get(id) ?? 0) < 2) continue
    const anchor = [...(anchors.get(id) ?? [])].sort((a, b) => (positions.get(a)?.x ?? 0) - (positions.get(b)?.x ?? 0) || a - b)[0]
    const x = positions.get(anchor)?.x ?? 0
    const parentBottom = Math.max(0, ...(parents.get(id) ?? []).map((parent) => (positions.get(parent)?.y ?? 0) + NODE_HEIGHT + ROW_GAP))
    const lastBottom = (columnBottom.get(anchor) ?? upperBottom) + ROW_GAP
    const y = Math.max(upperBottom + ROW_GAP, parentBottom, lastBottom)
    positions.set(id, { x, y })
    columnBottom.set(anchor, y + NODE_HEIGHT)
  }

  // Isolated employees are classified before collapse and occupy a separate grid below the hierarchy.
  const mainPoints = [...positions.values()]
  const mainLeft = Math.min(0, ...mainPoints.map((point) => point.x))
  const mainRight = Math.max(0, ...mainPoints.map((point) => point.x + NODE_WIDTH))
  const mainBottom = Math.max(0, ...mainPoints.map((point) => point.y + NODE_HEIGHT))
  const columns = Math.min(4, Math.max(1, isolated.length))
  const gridWidth = columns * NODE_WIDTH + (columns - 1) * COLUMN_GAP
  const gridLeft = mainLeft + Math.max(0, (mainRight - mainLeft - gridWidth) / 2)
  const gridTop = mainPoints.length ? mainBottom + ISOLATED_GAP : 0
  isolated.forEach((employee, index) => positions.set(employee.id, {
    x: gridLeft + (index % columns) * (NODE_WIDTH + COLUMN_GAP),
    y: gridTop + Math.floor(index / columns) * (NODE_HEIGHT + 20),
  }))

  return {
    nodes: graph.employees.map((employee) => ({
      id: String(employee.id),
      type: 'employee',
      position: positions.get(employee.id) ?? { x: 0, y: 0 },
      // React Flow otherwise sets pointer-events:none when dragging and selection are both disabled.
      style: { pointerEvents: 'all' },
      data: { employee },
    })),
    edges: graph.relationships.map((edge) => ({
      id: `${edge.superior_id}-${edge.employee_id}`,
      source: String(edge.superior_id),
      target: String(edge.employee_id),
      type: 'smoothstep',
      animated: false,
      style: graph.ancestors.has(edge.superior_id) && (graph.ancestors.has(edge.employee_id) || graph.matches.has(edge.employee_id))
        ? { stroke: 'var(--info)', strokeWidth: 2.5 }
        : graph.descendants.has(edge.employee_id) && (graph.matches.has(edge.superior_id) || graph.descendants.has(edge.superior_id))
          ? { stroke: 'var(--success)', strokeWidth: 2.5 }
          : undefined,
    })),
  }
}
