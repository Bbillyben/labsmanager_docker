import { describe, expect, it } from 'vitest'
import { employeeQuery, readEmployeeParams } from './employees'
import { projectQuery, readProjectParams } from './projects'

describe('shared list filter defaults', () => {
  it('materializes Active=true for Project and Employee, then permits its removal', () => {
    const project = readProjectParams(new URLSearchParams())
    const employee = readEmployeeParams(new URLSearchParams())
    expect(project.filters.get('status')).toBe('true')
    expect(employee.filters.get('is_active')).toBe('true')
    expect(projectQuery(project, true)).toContain('status=true')
    expect(employeeQuery(employee, true)).toContain('is_active=true')
    const withoutProjectActive = readProjectParams(new URLSearchParams('filters_initialized=1'))
    const withoutEmployeeActive = readEmployeeParams(new URLSearchParams('filters_initialized=1'))
    expect(withoutProjectActive.filters.has('status')).toBe(false)
    expect(withoutEmployeeActive.filters.has('is_active')).toBe(false)
    expect(withoutProjectActive.ordering).toBe('name')
  })

  it('keeps explicit inactive filters and validates sorting and pagination', () => {
    const params = readProjectParams(new URLSearchParams('status=false&ordering=-name&limit=10&offset=10'))
    expect(params.filters.get('status')).toBe('false')
    expect(params.ordering).toBe('-name')
    expect(params.limit).toBe(10)
    expect(params.offset).toBe(10)
  })
})
