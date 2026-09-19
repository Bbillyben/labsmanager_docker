import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../api/client'
import { authenticatedUser, jsonResponse } from '../test/fixtures'
import { useAuth } from './AuthContext'
import { AuthProvider } from './AuthProvider'

function AuthProbe() {
  const auth = useAuth()
  return <><p>{auth.status}</p><button onClick={() => void auth.refresh()} type="button">Actualiser</button></>
}

describe('AuthProvider', () => {
  it('bootstraps an authenticated Django session', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser))
    render(<AuthProvider><AuthProbe /></AuthProvider>)

    expect(screen.getByText('loading')).toBeInTheDocument()
    expect(await screen.findByText('authenticated')).toBeInTheDocument()
  })

  it('detects an anonymous or expired session', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ is_authenticated: false }))
    render(<AuthProvider><AuthProbe /></AuthProvider>)

    expect(await screen.findByText('unauthenticated')).toBeInTheDocument()
  })

  it('keeps transport failures distinct from unauthenticated sessions', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('network unavailable'))
    render(<AuthProvider><AuthProbe /></AuthProvider>)

    expect(await screen.findByText('error')).toBeInTheDocument()
  })

  it('switches to unauthenticated when a later API call receives 401', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(authenticatedUser))
      .mockResolvedValueOnce(jsonResponse({ detail: 'Unauthorized' }, 401))
    render(<AuthProvider><AuthProbe /></AuthProvider>)
    expect(await screen.findByText('authenticated')).toBeInTheDocument()

    await expect(apiRequest('/api/v1/private/')).rejects.toBeInstanceOf(Error)
    await waitFor(() => expect(screen.getByText('unauthenticated')).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('refreshes the current user after a session change', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ is_authenticated: false }))
      .mockResolvedValueOnce(jsonResponse(authenticatedUser))
    render(<AuthProvider><AuthProbe /></AuthProvider>)
    expect(await screen.findByText('unauthenticated')).toBeInTheDocument()

    screen.getByRole('button', { name: 'Actualiser' }).click()

    expect(await screen.findByText('authenticated')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
