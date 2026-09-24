import { describe, expect, it } from 'vitest'
import { ApiError, normalizeMutationError } from './errors'

describe('mutation errors', () => {
  it('separates field, non-field and detail messages', () => {
    expect(normalizeMutationError(new ApiError(400, { value: ['Too long'], type_id: ['Invalid'], non_field_errors: ['Conflict'], detail: 'Explanation' }))).toEqual({
      kind: 'validation', fields: { value: ['Too long'], type_id: ['Invalid'] }, messages: ['Conflict', 'Explanation'],
    })
  })
  it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'notFound'], [500, 'server'], [503, 'server']])('classifies HTTP %i', (status, kind) => {
    expect(normalizeMutationError(new ApiError(Number(status), undefined)).kind).toBe(kind)
  })
  it('recognizes network failures without inventing server messages', () => {
    expect(normalizeMutationError(new TypeError('fetch failed'))).toEqual({ kind: 'network', fields: {}, messages: [] })
  })
})
