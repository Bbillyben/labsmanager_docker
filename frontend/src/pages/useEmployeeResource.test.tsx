import { act, renderHook, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { useEmployeeResource } from './useEmployeeResource'

it('retains the server write when refresh fails and retries only the read', async () => {
  const loader = vi.fn().mockResolvedValueOnce(['old']).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(['saved'])
  const { result } = renderHook(() => useEmployeeResource<string[]>('1', loader))
  await waitFor(() => expect(result.current.data).toEqual(['old']))
  act(() => result.current.updateData(() => ['saved']))
  await act(async () => { expect(await result.current.refresh()).toBe(false) })
  expect(result.current.data).toEqual(['saved'])
  expect(result.current.error).toBeNull()
  expect(result.current.refreshError).toBeInstanceOf(Error)
  await act(async () => { expect(await result.current.refresh()).toBe(true) })
  expect(result.current.refreshError).toBeNull()
  expect(loader).toHaveBeenCalledTimes(3)
})

it('ignores an old read after a server write and isolates Employee changes', async () => {
  let resolve!: (data: string[]) => void
  const loader = vi.fn().mockResolvedValueOnce(['first']).mockImplementationOnce(() => new Promise<string[]>((done) => { resolve = done })).mockResolvedValueOnce(['second'])
  const { result, rerender } = renderHook(({ id }) => useEmployeeResource<string[]>(id, loader), { initialProps: { id: '1' } })
  await waitFor(() => expect(result.current.data).toEqual(['first']))
  let refresh!: Promise<boolean>
  act(() => { refresh = result.current.refresh() })
  act(() => result.current.updateData(() => ['written']))
  await act(async () => { resolve(['stale']); await refresh })
  expect(result.current.data).toEqual(['written'])
  rerender({ id: '2' })
  await waitFor(() => expect(result.current.data).toEqual(['second']))
})
