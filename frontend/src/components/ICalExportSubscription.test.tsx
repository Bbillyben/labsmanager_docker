import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { SubscriptionDialog } from '../../../backend/plugin/builtin/ICalExport/frontend/src/main'

afterEach(() => vi.restoreAllMocks())

it('creates a published URL only on confirmation, then copies it and invalidates it after an option change', async () => {
  const calls: string[] = []
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
    calls.push(String(init?.body))
    return jsonResponse({ url: 'https://labs.example.org/plugin/icalexport/ics/external/calendars/5/?token=secret&assigned_to_me=1' })
  })
  const writeText = vi.fn(async () => undefined)
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
  const onClose = vi.fn()
  render(<I18nProvider><SubscriptionDialog context={{ name: 'Équipe', actionUrl: '/api/v1/demo/',
    options: ['assigned_to_me'] }} onClose={onClose} /></I18nProvider>)
  expect(await screen.findByText('Équipe')).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('checkbox'))
  await userEvent.click(screen.getByRole('button', { name: 'Create link' }))
  expect(await screen.findByDisplayValue(/assigned_to_me=1/)).toBeInTheDocument()
  expect(calls).toEqual(['{"assigned_to_me":true}'])
  expect(writeText).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Copy' }))
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('token=secret')))
  expect(await screen.findByRole('status')).toHaveTextContent('Link copied.')
  await userEvent.click(screen.getByRole('checkbox'))
  expect(screen.queryByDisplayValue(/assigned_to_me=1/)).not.toBeInTheDocument()
  expect(onClose).not.toHaveBeenCalled()
}, 15000)

it('uses plugin translations and follows a language change while the sheet is open', async () => {
  const previous = Object.getOwnPropertyDescriptor(navigator, 'languages')
  try {
    Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ url: 'https://labs.example.org/ics/?token=secret' }))
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn(async () => undefined) } })
    render(<I18nProvider><SubscriptionDialog context={{ name: 'Équipe', actionUrl: '/api/v1/demo/', options: ['assigned_to_me'] }} /></I18nProvider>)
    expect(await screen.findByText('S’abonner au calendrier')).toBeInTheDocument()
    expect(screen.getByText('Uniquement les événements qui me concernent')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Créer le lien' }))
    await screen.findByDisplayValue(/token=secret/)
    await userEvent.click(screen.getByRole('button', { name: 'Copier' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Lien copié.')
    Object.defineProperty(navigator, 'languages', { configurable: true, value: ['en-US'] })
    window.dispatchEvent(new Event('languagechange'))
    expect(await screen.findByText('Subscribe to calendar')).toBeInTheDocument()
    expect(screen.getByText('Only events assigned to me')).toBeInTheDocument()
    expect(await screen.findByRole('status')).toHaveTextContent('Link copied.')
  } finally {
    if (previous) Object.defineProperty(navigator, 'languages', previous)
  }
})
