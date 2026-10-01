import { describe, expect, it, vi } from 'vitest'
import { getDjangoUrl } from './django'

describe('getDjangoUrl', () => {
  it('keeps root-relative Django paths when no public origin is configured', () => {
    expect(getDjangoUrl('/accounts/password/reset/')).toBe('/accounts/password/reset/')
  })

  it('rejects external and protocol-relative paths', () => {
    expect(() => getDjangoUrl('https://example.test')).toThrow('root-relative')
    expect(() => getDjangoUrl('//example.test')).toThrow('root-relative')
  })

  it('uses the configured Django origin for Admin links', async () => {
    vi.stubEnv('VITE_DJANGO_PUBLIC_URL', 'http://django.example:7000')
    vi.resetModules()
    try {
      const { getDjangoUrl: configuredUrl } = await import('./django')
      expect(configuredUrl('/admin/staff/employee/73/change/')).toBe('http://django.example:7000/admin/staff/employee/73/change/')
    } finally {
      vi.unstubAllEnvs()
      vi.resetModules()
    }
  })
})
