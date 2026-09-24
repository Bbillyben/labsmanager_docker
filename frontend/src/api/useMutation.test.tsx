import { act, renderHook } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { useMutation } from './useMutation'

it('prevents simultaneous submissions including within the same render', async () => {
  let resolve!: (value: string) => void
  const write = vi.fn(() => new Promise<string>((done) => { resolve = done }))
  const { result } = renderHook(useMutation)
  let first!: ReturnType<typeof result.current.run>
  await act(async () => {
    first = result.current.run(write)
    expect(await result.current.run(write)).toBeUndefined()
  })
  expect(result.current.pending).toBe(true)
  expect(write).toHaveBeenCalledTimes(1)
  await act(async () => { resolve('saved'); expect(await first).toEqual({ data: 'saved' }) })
  expect(result.current.pending).toBe(false)
})

it('retains the error and allows a deliberate retry', async () => {
  const { result } = renderHook(useMutation)
  const error = new Error('failed')
  await act(async () => { expect(await result.current.run(() => Promise.reject(error))).toBeUndefined() })
  expect(result.current.error).toBe(error)
  await act(async () => { expect(await result.current.run(async () => undefined)).toEqual({ data: undefined }) })
  expect(result.current.error).toBeNull()
})


it('does not deliver a late write result to an unmounted form', async () => {
  let resolve!: (value: string) => void
  const { result, unmount } = renderHook(useMutation)
  let write!: ReturnType<typeof result.current.run>
  act(() => { write = result.current.run(() => new Promise<string>((done) => { resolve = done })) })
  unmount()
  resolve('saved on the server')
  expect(await write).toBeUndefined()
})
