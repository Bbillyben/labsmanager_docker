import { afterEach, describe, expect, it, vi } from 'vitest'
import { getSearchAutocomplete, getSearchSchema, search } from './globalSearch'

afterEach(() => vi.restoreAllMocks())

describe('Global Search API client', () => {
  it('passes query, provider, limits and cancellation to the existing API client', async () => {
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ query: 'Jean Dupont', results: [], groups: {} }), { status: 200, headers: { 'content-type': 'application/json' } }))
    const controller = new AbortController()
    await search('Jean Dupont', { provider: 'employee', limit: 9, perProvider: 3, signal: controller.signal })
    const [url, init] = fetcher.mock.calls[0]
    expect(new URL(String(url), 'http://localhost').searchParams.get('q')).toBe('Jean Dupont')
    expect(new URL(String(url), 'http://localhost').searchParams.get('provider')).toBe('employee')
    expect(new URL(String(url), 'http://localhost').searchParams.get('limit')).toBe('9')
    expect(new URL(String(url), 'http://localhost').searchParams.get('per_provider')).toBe('3')
    expect(init?.signal).toBe(controller.signal)
  })

  it('fetches the active provider schema', async () => {
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ providers: [] }), { status: 200, headers: { 'content-type': 'application/json' } }))
    expect(await getSearchSchema()).toEqual({ providers: [] })
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/search/schema/')
  })

  it('sends the full query and caret position for contextual completion', async () => {
    const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ context: 'key', suggestions: [], replace_start: 4, replace_end: 7 }), { status: 200, headers: { 'content-type': 'application/json' } }))
    const controller = new AbortController()
    await getSearchAutocomplete('foo lea:bar', 7, { provider: 'project', signal: controller.signal })
    const [url, init] = fetcher.mock.calls[0]
    const parsed = new URL(String(url), 'http://localhost')
    expect(parsed.pathname).toBe('/api/v1/search/autocomplete/')
    expect(parsed.searchParams.get('q')).toBe('foo lea:bar')
    expect(parsed.searchParams.get('cursor')).toBe('7')
    expect(parsed.searchParams.get('provider')).toBe('project')
    expect(init?.signal).toBe(controller.signal)
  })
})
