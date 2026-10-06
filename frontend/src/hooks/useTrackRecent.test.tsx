import { renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { useTrackRecent } from './useTrackRecent'

const track = vi.hoisted(() => vi.fn())
vi.mock('../api/recentItems', () => ({ trackRecentItem: track }))

beforeEach(() => { track.mockReset(); track.mockResolvedValue({}) })

it('tracks only after a destination opens, once per mounted destination', () => {
  const result = renderHook(({ id, ready }) => useTrackRecent('project', id, ready), { initialProps: { id: 42, ready: false } })
  expect(track).not.toHaveBeenCalled()
  result.rerender({ id: 42, ready: true })
  expect(track).toHaveBeenCalledOnce()
  expect(track).toHaveBeenCalledWith('project', 42)
  result.rerender({ id: 42, ready: true })
  expect(track).toHaveBeenCalledOnce()
  result.rerender({ id: 43, ready: true })
  expect(track).toHaveBeenCalledTimes(2)
})

it('tracks a page without an object id', () => {
  renderHook(() => useTrackRecent('calendar'))
  expect(track).toHaveBeenCalledWith('calendar', undefined)
})
