import { describe, expect, it } from 'vitest'
import { changeFilter, readFilterQuery, resetFilters } from './url'
import type { SupportedFilter } from './types'

const flag: SupportedFilter = { id: 'flag', label: 'État', category: 'Général', type: 'static-choice', parameter: 'flag', options: [{ value: 'yes', label: 'Oui' }] }
const owner: SupportedFilter = { id: 'owner', label: 'Responsable', category: 'Liens', type: 'entity-search', parameter: 'owner', source: 'people', idFormat: 'positive-integer' }
const catalogue = [flag, owner]

describe('filter URL state', () => {
  it('preserves an added empty control and restores stable IDs', () => {
    expect(readFilterQuery(catalogue, new URLSearchParams('flag=&owner=42&search=test')).toString()).toBe('flag=&owner=42')
  })
  it('ignores invalid values and keeps a single occurrence', () => {
    expect(readFilterQuery(catalogue, new URLSearchParams('flag=bad&owner=-3')).toString()).toBe('')
    expect(readFilterQuery(catalogue, new URLSearchParams('flag=yes&flag=no')).toString()).toBe('flag=yes')
  })
  it('updates, removes and resets only owned parameters plus supplied pagination', () => {
    const initial = new URLSearchParams('search=test&ordering=name&offset=25&flag=yes&owner=42')
    expect(changeFilter(initial, flag, '', ['offset']).toString()).toBe('search=test&ordering=name&flag=&owner=42')
    expect(changeFilter(initial, owner, null, ['offset']).has('owner')).toBe(false)
    expect(resetFilters(initial, catalogue, ['offset']).toString()).toBe('search=test&ordering=name')
    expect(initial.get('offset')).toBe('25')
  })
})
