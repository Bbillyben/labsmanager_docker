import { describe, expect, it } from 'vitest'
import { planningFilterQuery } from './planning'

describe('Planning filters', () => {
  it('keeps the unfiltered Employee request unchanged', () => {
    expect(planningFilterQuery()).toBe('')
  })

  it('serializes optional Planning filters for the backend queryset', () => {
    expect(planningFilterQuery({ search: '  budget report  ', kind: 'task' })).toBe('?search=budget+report&kind=task')
    expect(planningFilterQuery({ search: 'Atlas', kind: 'milestone', employee: '7' })).toBe('?search=Atlas&kind=milestone&employee=7')
  })
})
