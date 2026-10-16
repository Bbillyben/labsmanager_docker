import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { UserSettingsSection } from './SettingsHubPage'
import type { UserSettingData } from '../api/userSettings'

const authState = vi.hoisted(() => ({ employee: null as { id: number; name: string } | null }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ status: 'authenticated', user: { employee: authState.employee, theme: 'light' } }) }))

const sendUrl = '/api/v1/settings/notifications/test-email/send/'
const previewUrl = '/api/v1/settings/notifications/test-email/preview/'
const mount = () => render(<I18nProvider><UserSettingsSection section="notifications" /></I18nProvider>)
const generalKeys = ['NOTIFCATION_STATUS', 'NOTIFCATION_REPORT_LANGUAGE']
const activityKeys = [
  'NOTIFICATION_PROJECT_PARTICIPANT', 'NOTIFICATION_STAFF_EMPLOYEE',
  'NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT', 'NOTIFICATION_ENDPOINTS_MILESTONES',
]
const periodicKeys = [
  'NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_REPEAT', 'NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_HORIZON',
  'NOTIFCATION_FREQ', 'NOTIFCATION_EMP_INCOMMING', 'NOTIFCATION_INC_LEAVE',
  'NOTIFCATION_SUB_MILESTONES', 'NOTIFCATION_LEAVE_FORMAT',
  'NOTIFCATION_LEAVE_REPORT_NONE', 'NOTIFCATION_LEAVE_TIMEFRAME',
]
const integerKeys = new Set([
  'NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT',
  'NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_REPEAT', 'NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_HORIZON',
])
const choiceKeys = new Set(['NOTIFCATION_REPORT_LANGUAGE', 'NOTIFCATION_FREQ', 'NOTIFCATION_LEAVE_FORMAT', 'NOTIFCATION_LEAVE_TIMEFRAME'])
const choiceValues: Record<string, string> = {
  NOTIFCATION_REPORT_LANGUAGE: 'en', NOTIFCATION_FREQ: '3 5 * * 5',
  NOTIFCATION_LEAVE_FORMAT: 'calendar', NOTIFCATION_LEAVE_TIMEFRAME: '31days',
}
const choiceOptions: Record<string, { value: string; label: string }[]> = {
  NOTIFCATION_REPORT_LANGUAGE: [{ value: 'en', label: 'English' }, { value: 'fr', label: 'French' }],
  NOTIFCATION_FREQ: [{ value: '3 5 * * 5', label: 'Weekly' }],
  NOTIFCATION_LEAVE_FORMAT: [{ value: 'calendar', label: 'Calendar' }, { value: 'list', label: 'List' }],
  NOTIFCATION_LEAVE_TIMEFRAME: [{ value: '31days', label: '31 days' }],
}
const settings: UserSettingData[] = [...generalKeys, ...activityKeys, ...periodicKeys].map((key) => ({
  key, name: key, description: `${key} description`,
  type: integerKeys.has(key) ? 'integer' : choiceKeys.has(key) ? 'choice' : 'boolean',
  value: integerKeys.has(key) ? 7 : choiceKeys.has(key) ? choiceValues[key] : true,
  default: integerKeys.has(key) ? 7 : choiceKeys.has(key) ? choiceValues[key] : true,
  choices: choiceOptions[key] ?? [],
  can_change: true,
}))

describe('Settings notification tests', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
  })
  afterEach(() => { vi.restoreAllMocks(); authState.employee = null })

  it('groups every existing setting once by its real consumer and keeps the three sections visible without an Employee', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ settings }))
    mount()
    const general = await screen.findByRole('region', { name: 'General notifications' })
    const activity = screen.getByRole('region', { name: 'Notifications about my activity' })
    const periodic = screen.getByRole('region', { name: 'Periodic email report' })
    for (const [region, keys] of [[general, generalKeys], [activity, activityKeys], [periodic, periodicKeys]] as const) {
      for (const key of keys) expect(within(region).getByLabelText(key)).toBeInTheDocument()
    }
    for (const key of [...generalKeys, ...activityKeys, ...periodicKeys]) expect(screen.getAllByLabelText(key)).toHaveLength(1)
    expect(screen.queryByLabelText('NOTIFICATION_ENDPOINTS_MILESTONES_STALE')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('DASHBOARD_MILESTONES_STALE_TO_DAYS')).not.toBeInTheDocument()
    expect(within(periodic).getByRole('button', { name: 'Preview notification' })).toBeInTheDocument()
  })

  it('shows the three section titles in French', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ settings: [] }))
    mount()
    expect(await screen.findByRole('region', { name: 'Notifications générales' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Notifications liées à mon activité' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Rapport périodique par email' })).toBeInTheDocument()
  })

  it('keeps immediate saves, list/calendar choices and API errors with a linked Employee', async () => {
    authState.employee = { id: 7, name: 'Ada' }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options) => {
      if (String(url).includes('/api/v1/settings/user/notifications/') && options?.method === 'PATCH') {
        const key = String(url).split('/').at(-2)
        const value = JSON.parse(String(options.body)).value
        if (key === 'NOTIFICATION_PROJECT_PARTICIPANT') return jsonResponse({ value: ['Invalid value'] }, 400)
        return jsonResponse({ ...settings.find((setting) => setting.key === key), value })
      }
      return jsonResponse({ settings })
    })
    mount()
    const format = await screen.findByLabelText('NOTIFCATION_LEAVE_FORMAT')
    expect(format).toHaveValue('calendar')
    await userEvent.selectOptions(format, 'list')
    expect(format).toHaveValue('list')
    expect(fetch.mock.calls.some(([url, options]) => String(url).endsWith('/NOTIFCATION_LEAVE_FORMAT/') && options?.body === JSON.stringify({ value: 'list' }))).toBe(true)
    await userEvent.click(screen.getByLabelText('NOTIFICATION_PROJECT_PARTICIPANT'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid value')
    expect(screen.getByLabelText('NOTIFICATION_PROJECT_PARTICIPANT')).toBeChecked()
  })

  it('shows and saves the day threshold only in Stale alerts', async () => {
    const threshold: UserSettingData = {
      key: 'DASHBOARD_MILESTONES_STALE_TO_DAYS', name: 'Milestone upcoming threshold (days)',
      description: 'Number of days before a milestone deadline at which it is considered upcoming.',
      type: 'integer', value: 90, default: 90, choices: [], can_change: true,
    }
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, options) => {
      if (options?.method === 'PATCH') return jsonResponse({ ...threshold, value: JSON.parse(String(options.body)).value })
      return jsonResponse({ settings: [threshold] })
    })
    render(<I18nProvider><UserSettingsSection section="stale" /></I18nProvider>)
    const input = await screen.findByLabelText('Milestone upcoming threshold (days)')
    expect(input).toHaveValue(90)
    expect(screen.queryByLabelText('DASHBOARD_MILESTONES_STALE_TO_MONTH')).not.toBeInTheDocument()
    await userEvent.clear(input)
    await userEvent.type(input, '45')
    await userEvent.tab()
    await waitFor(() => expect(fetch.mock.calls.some(([url, options]) =>
      String(url).endsWith('/stale/DASHBOARD_MILESTONES_STALE_TO_DAYS/') && options?.body === JSON.stringify({ value: 45 }),
    )).toBe(true))
  })

  it('sends for the current session, blocks double clicks, and reports success', async () => {
    let complete!: (value: Response) => void
    const pending = new Promise<Response>((resolve) => { complete = resolve })
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === sendUrl ? pending : jsonResponse({ settings: [] }))
    mount()
    const button = await screen.findByRole('button', { name: 'Send test notification' })
    expect(screen.getByRole('button', { name: 'Preview notification' })).toBeInTheDocument()
    await userEvent.click(button)
    expect(button).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Preview notification' })).toBeDisabled()
    expect(fetch.mock.calls.filter(([url]) => String(url) === sendUrl)).toHaveLength(1)
    const call = fetch.mock.calls.find(([url]) => String(url) === sendUrl)?.[1]
    expect(call?.method).toBe('POST')
    expect(call?.credentials).toBe('include')
    expect(call?.body).toBeUndefined()
    complete(jsonResponse({ sent: true }))
    expect(await screen.findByRole('status')).toHaveTextContent('Test notification sent.')
    await waitFor(() => expect(button).toBeEnabled())
  })

  it('opens preview synchronously, writes backend HTML and handles errors', async () => {
    let complete!: (value: Response) => void
    const pending = new Promise<Response>((resolve) => { complete = resolve })
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === previewUrl ? pending : jsonResponse({ settings: [] }))
    const popup = {
      document: { open: vi.fn(), write: vi.fn(), close: vi.fn(), title: '', body: { style: { backgroundColor: '' } } },
      close: vi.fn(),
    }
    const open = vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window)
    mount()
    await userEvent.click(await screen.findByRole('button', { name: 'Preview notification' }))
    expect(open).toHaveBeenCalledOnce()
    expect(fetch.mock.calls.find(([url]) => String(url) === previewUrl)?.[1]?.body).toBeUndefined()
    complete(new Response('<html><body>Mail preview</body></html>', { headers: { 'content-type': 'text/html' } }))
    await waitFor(() => expect(popup.document.write).toHaveBeenCalledWith('<html><body>Mail preview</body></html>'))
    expect(popup.document.title).toBe('LabsManager Test Mail')
    expect(popup.document.body.style.backgroundColor).toBe('white')

    fetch.mockImplementation(async (url) => String(url) === previewUrl ? jsonResponse({ detail: 'Preview failed' }, 500) : jsonResponse({ settings: [] }))
    await userEvent.click(screen.getByRole('button', { name: 'Preview notification' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to generate the notification preview.')
    expect(popup.close).toHaveBeenCalledOnce()
  })

  it('reports a send error and keeps the controls usable', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => String(url) === sendUrl ? jsonResponse({ detail: 'No verified primary email' }, 400) : jsonResponse({ settings: [] }))
    mount()
    const button = await screen.findByRole('button', { name: 'Send test notification' })
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('No verified primary email')
    expect(button).toBeEnabled()
  })
})
