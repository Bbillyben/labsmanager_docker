import { describe, expect, it } from 'vitest'
import type { ChartEmployee, ChartRelationship } from '../api/organizationChart'
import { buildOrganizationGraph, organizationHighlight } from './organizationGraph'

const employees: ChartEmployee[] = [1, 2, 3, 4, 5].map((id) => ({ id, name: `Employee ${id}`, is_active: true, statuses: [], can_view: true }))
const relationships: ChartRelationship[] = [
  { superior_id: 1, employee_id: 3 },
  { superior_id: 2, employee_id: 3 },
  { superior_id: 3, employee_id: 4 },
  { superior_id: 1, employee_id: 5 },
]

describe('organization graph', () => {
  it('keeps one node with two incoming relationships and derives independent roots', () => {
    const graph = buildOrganizationGraph(employees, relationships, new Set(), '')
    expect(graph.roots).toEqual([1, 2])
    expect(graph.employees.map((employee) => employee.id)).toEqual([1, 2, 3, 4, 5])
    expect(graph.relationships.filter((relation) => relation.employee_id === 3)).toHaveLength(2)
  })

  it('keeps a child visible through its other superior and hides descendants only after both paths close', () => {
    const once = buildOrganizationGraph(employees, relationships, new Set([1]), '')
    expect(once.employees.map((employee) => employee.id)).toEqual([1, 2, 3, 4])
    expect(once.relationships.some((edge) => edge.superior_id === 1)).toBe(false)
    const twice = buildOrganizationGraph(employees, relationships, new Set([1, 2]), '')
    expect(twice.employees.map((employee) => employee.id)).toEqual([1, 2])
  })

  it('temporarily opens every ancestor path for search without clearing manual collapse', () => {
    const collapsed = new Set([1, 2])
    const graph = buildOrganizationGraph(employees, relationships, collapsed, 'employee 4')
    expect([...graph.matches]).toEqual([4])
    expect([...graph.highlighted].sort()).toEqual([1, 2, 3, 4])
    expect(graph.employees.map((employee) => employee.id)).toEqual([1, 2, 3, 4])
    expect(collapsed).toEqual(new Set([1, 2]))
  })

  it('does not reveal filtered employees through an edge', () => {
    const graph = buildOrganizationGraph(employees.slice(0, 2), relationships, new Set(), '')
    expect(graph.relationships).toEqual([])
  })

  it('highlights every matching employee and all ancestor paths', () => {
    const rows = employees.map((employee) => ({ ...employee, name: employee.id === 3 || employee.id === 5 ? 'Sam Example' : employee.name }))
    const graph = buildOrganizationGraph(rows, relationships, new Set(), 'sam')
    expect([...graph.matches]).toEqual([3, 5])
    expect([...graph.highlighted].sort()).toEqual([1, 2, 3, 4, 5])
  })

  it('distinguishes a match, all parents and descendants in a multi-parent DAG', () => {
    const graph = buildOrganizationGraph(employees, relationships, new Set(), 'employee 3')
    expect([...graph.matches]).toEqual([3])
    expect([...graph.ancestors].sort()).toEqual([1, 2])
    expect([...graph.descendants]).toEqual([4])
  })

  it('keeps descendants highlighted only when visible and preserves manual collapse after search', () => {
    const collapsed = new Set([3])
    const search = buildOrganizationGraph(employees, relationships, collapsed, 'employee 3')
    expect(search.descendants.has(4)).toBe(true)
    expect(search.employees.some((employee) => employee.id === 4)).toBe(false)
    expect(buildOrganizationGraph(employees, relationships, collapsed, '').employees.some((employee) => employee.id === 4)).toBe(false)
    expect(collapsed.has(3)).toBe(true)
  })

  it('classifies isolated employees before collapse, but not roots with children', () => {
    const rows = employees.slice(0, 3)
    const edges = [{ superior_id: 1, employee_id: 2 }]
    const graph = buildOrganizationGraph(rows, edges, new Set([1]), '')
    expect([...graph.isolated]).toEqual([3])
    expect(graph.isolated.has(1)).toBe(false)
    expect(graph.employees.map((employee) => employee.id)).toEqual([1, 3])
  })

  it('retains inactive employees as searchable, visible nodes', () => {
    const rows = [{ ...employees[0], is_active: false }, employees[1]]
    const graph = buildOrganizationGraph(rows, [{ superior_id: 1, employee_id: 2 }], new Set(), 'employee 1')
    expect(graph.employees[0].is_active).toBe(false)
    expect(graph.matches.has(1)).toBe(true)
  })

  it('prioritizes match over ancestor and ancestor over descendant', () => {
    const rows = [employees[0], employees[1], employees[2]].map((employee, index) => ({ ...employee, name: index === 1 ? 'Middle' : 'Target' }))
    const graph = buildOrganizationGraph(rows, [
      { superior_id: 1, employee_id: 2 },
      { superior_id: 2, employee_id: 3 },
    ], new Set(), 'target')
    expect(organizationHighlight(graph, 1)).toBe('match')
    expect(organizationHighlight(graph, 2)).toBe('ancestor')
    expect(organizationHighlight(graph, 3)).toBe('match')
  })
})
