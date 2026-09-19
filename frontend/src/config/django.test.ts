import { describe, expect, it } from 'vitest'
import { getDjangoUrl } from './django'

describe('getDjangoUrl', () => {
  it('keeps root-relative Django paths when no public origin is configured', () => {
    expect(getDjangoUrl('/accounts/password/reset/')).toBe('/accounts/password/reset/')
  })

  it('rejects external and protocol-relative paths', () => {
    expect(() => getDjangoUrl('https://example.test')).toThrow('root-relative')
    expect(() => getDjangoUrl('//example.test')).toThrow('root-relative')
  })
})
