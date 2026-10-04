import { describe, expect, it } from 'vitest'
import type { ChartEmployee } from '../api/organizationChart'
import { buildOrganizationGraph } from './organizationGraph'
import { layoutOrganizationGraph } from './organizationLayout'

const employee = (id: number): ChartEmployee => ({ id, name: `Employee ${id}`, is_active: true, statuses: [], can_view: true })

describe('organization layout', () => {
  it('keeps the upper hierarchy in ELK, stacks deeper siblings and grids isolated employees below', async () => {
    const graph = buildOrganizationGraph(Array.from({ length: 8 }, (_, index) => employee(index + 1)), [
      { superior_id: 1, employee_id: 2 },
      { superior_id: 2, employee_id: 3 },
      { superior_id: 2, employee_id: 4 },
      { superior_id: 2, employee_id: 5 },
      { superior_id: 3, employee_id: 6 },
      { superior_id: 8, employee_id: 4 },
    ], new Set(), '')
    const layout = await layoutOrganizationGraph(graph)
    const positions = new Map(layout.nodes.map((node) => [Number(node.id), node.position]))
    expect(layout.nodes).toHaveLength(8)
    expect(layout.edges).toHaveLength(6)
    expect(positions.get(2)!.y).toBeGreaterThan(positions.get(1)!.y)
    expect(positions.get(3)!.x).toBe(positions.get(4)!.x)
    expect(positions.get(4)!.x).toBe(positions.get(5)!.x)
    expect(positions.get(3)!.y).not.toBe(positions.get(4)!.y)
    expect(positions.get(6)!.y).toBeGreaterThan(positions.get(3)!.y)
    expect(positions.get(7)!.y).toBeGreaterThan(Math.max(...[1, 2, 3, 4, 5, 6, 8].map((id) => positions.get(id)!.y)))
    expect(layout.nodes.every((node) => node.style?.pointerEvents === 'all')).toBe(true)
  })

  it('does not move a collapsed hierarchy root into the isolated group', async () => {
    const graph = buildOrganizationGraph([employee(1), employee(2), employee(3)], [
      { superior_id: 1, employee_id: 2 },
    ], new Set([1]), '')
    const layout = await layoutOrganizationGraph(graph)
    const root = layout.nodes.find((node) => node.id === '1')!
    const isolated = layout.nodes.find((node) => node.id === '3')!
    expect(layout.nodes.map((node) => node.id)).toEqual(['1', '3'])
    expect(root.position.y).toBeLessThan(isolated.position.y)
  })
})
