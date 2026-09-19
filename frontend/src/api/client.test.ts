import { describe, expect, it, vi } from 'vitest'
import { apiRequest, subscribeToUnauthorized } from './client'
import { jsonResponse } from '../test/fixtures'

describe('apiRequest', () => {
  it('uses same-origin session credentials and returns JSON', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ ok: true }))

    await expect(apiRequest<{ ok: boolean }>('/api/v1/me/')).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/me/', expect.objectContaining({ credentials: 'include', method: 'GET' }))
  })

  it('adds the Django CSRF cookie to unsafe requests', async () => {
    document.cookie = 'csrftoken=token%20value'
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))

    await apiRequest<void>('/api/v1/example/', { method: 'POST' })
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(new Headers(init.headers).get('X-CSRFToken')).toBe('token value')
  })

  it('returns undefined for an empty successful response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
    await expect(apiRequest<void>('/api/v1/example/')).resolves.toBeUndefined()
  })

  it('reports 401 globally and preserves the typed API error', async () => {
    const listener = vi.fn()
    const unsubscribe = subscribeToUnauthorized(listener)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: 'Unauthorized' }, 401))

    await expect(apiRequest('/api/v1/private/')).rejects.toMatchObject({ status: 401, payload: { detail: 'Unauthorized' } })
    expect(listener).toHaveBeenCalledOnce()
    unsubscribe()
  })

  it('does not turn a 403 into a global session expiration', async () => {
    const listener = vi.fn()
    const unsubscribe = subscribeToUnauthorized(listener)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: 'Forbidden' }, 403))

    await expect(apiRequest('/api/v1/private/')).rejects.toMatchObject({ status: 403 })
    expect(listener).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('does not turn a login validation error into a global session expiration', async () => {
    const listener = vi.fn()
    const unsubscribe = subscribeToUnauthorized(listener)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ error: { code: 'invalid_credentials' } }, 400))

    await expect(apiRequest('/api/v1/auth/login/', { method: 'POST' })).rejects.toMatchObject({ status: 400 })
    expect(listener).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('rejects absolute URLs', async () => {
    await expect(apiRequest('https://example.test/api')).rejects.toThrow('relative')
  })
})
