import { afterEach, describe, expect, it, vi } from 'vitest'
import { copyPluginToken } from './copyPluginToken'

describe('plugin token copying', () => {
  afterEach(() => vi.restoreAllMocks())

  it('uses the Clipboard API when available', async () => {
    const input = document.createElement('input')
    input.value = 'public.private'
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    expect(await copyPluginToken(input)).toBe(true)
    expect(writeText).toHaveBeenCalledWith('public.private')
  })

  it('selects the whole token and reports failure if HTTP fallback cannot copy it', async () => {
    const input = document.createElement('input')
    input.value = 'public.private'
    document.body.append(input)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined })
    Object.defineProperty(document, 'execCommand', { configurable: true, value: vi.fn(() => false) })
    expect(await copyPluginToken(input)).toBe(false)
    expect(input.selectionStart).toBe(0)
    expect(input.selectionEnd).toBe(input.value.length)
    input.remove()
  })
})
