import { describe, expect, it } from 'vitest'
import { projectCalendarRange, shiftProjectCalendarAnchor, type ProjectCalendarScope } from './projectCalendarScopes'

describe('Project Calendar temporal scopes', () => {
  const anchor = new Date(2028, 0, 31)
  it.each([
    ['fifteenDays', { from: '2028-01-31', to: '2028-02-14' }, '2028-02-15', '2028-01-16'],
    ['month', { from: '2028-01-01', to: '2028-01-31' }, '2028-02-01', '2027-12-01'],
    ['twoMonths', { from: '2028-01-01', to: '2028-02-29' }, '2028-03-01', '2027-11-01'],
    ['year', { from: '2028-01-01', to: '2028-12-31' }, '2029-01-01', '2027-01-01'],
  ] as Array<[ProjectCalendarScope, { from: string; to: string }, string, string]>)('%s has bounded dates and exact navigation', (scope, range, next, previous) => {
    expect(projectCalendarRange(scope, anchor)).toEqual(range)
    expect(projectCalendarRange('fifteenDays', shiftProjectCalendarAnchor(anchor, scope, 1)).from).toBe(next)
    expect(projectCalendarRange('fifteenDays', shiftProjectCalendarAnchor(anchor, scope, -1)).from).toBe(previous)
  })
})
