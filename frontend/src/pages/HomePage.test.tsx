import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser } from '../test/fixtures'
import { HomePage } from './HomePage'

const mocks = vi.hoisted(() => ({ listDashboards: vi.fn(), listRecentItems: vi.fn(), useAuth: vi.fn() }))
vi.mock('../api/dashboards', () => ({ listDashboards: mocks.listDashboards }))
vi.mock('../api/recentItems', () => ({ listRecentItems: mocks.listRecentItems }))
vi.mock('../auth/AuthContext', () => ({ useAuth: mocks.useAuth }))

function showHome() {
  return render(<I18nProvider><MemoryRouter><HomePage /></MemoryRouter></I18nProvider>)
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  mocks.listDashboards.mockReset()
  mocks.listRecentItems.mockReset()
  mocks.useAuth.mockReset()
  mocks.useAuth.mockReturnValue({ status: 'authenticated', user: authenticatedUser })
  mocks.listDashboards.mockResolvedValue([
    { id: 2, name: 'Another board', icon: '', is_default: false, position: 0, scope: 'user' },
    { id: 7, name: 'My default', icon: '', is_default: true, position: 1, scope: 'user' },
  ])
  mocks.listRecentItems.mockResolvedValue([])
})

describe('Home hub', () => {
  it('links the default and other dashboards without loading widgets', async () => {
    showHome()
    expect(await screen.findByRole('link', { name: /My default/ })).toHaveAttribute('href', '/dashboard?selected=7')
    expect(screen.getByRole('link', { name: 'Another board' })).toHaveAttribute('href', '/dashboard?selected=2')
    expect(screen.getByText('Vos pages récemment consultées apparaîtront ici.')).toBeInTheDocument()
  })

  it('renders object and page destinations supplied by the backend', async () => {
    mocks.listRecentItems.mockResolvedValue([
      { url_id: 'fund', obj_id: 130, type: 'fund', title: 'ANR-42', subtitle: 'Atlas', icon: 'PiggyBank', url: '/app/projects/98/funding#fund-row-130', last_viewed_at: '' },
      { url_id: 'calendar', obj_id: null, type: 'calendar', title: 'Calendar', subtitle: '', icon: 'CalendarDays', url: '/app/calendars', last_viewed_at: '' },
    ])
    showHome()
    expect(await screen.findByRole('link', { name: /ANR-42/ })).toHaveAttribute('href', '/projects/98/funding#fund-row-130')
    expect(within(screen.getByRole('region', { name: 'Reprendre' })).getByRole('link', { name: 'Calendriers' })).toHaveAttribute('href', '/calendars')
  })

  it('filters quick access with existing navigation capabilities', async () => {
    mocks.useAuth.mockReturnValue({ status: 'authenticated', user: { ...authenticatedUser, capabilities: {
      ...authenticatedUser.capabilities, view_calendar: false, view_project_list: false,
      view_employee_list: false, view_team_list: false, use_fund_finder: false,
    } } })
    showHome()
    await screen.findByText('Vos pages récemment consultées apparaîtront ici.')
    expect(within(screen.getByRole('region', { name: 'Accès rapides' })).getAllByRole('link')).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'Explorateur de fonds' })).toHaveAttribute('href', '/tools/fund-items')
  })

  it('sends first-time users to the existing dashboard onboarding', async () => {
    mocks.listDashboards.mockResolvedValue([])
    showHome()
    expect(await screen.findByRole('link', { name: /Créer mon tableau de bord/ })).toHaveAttribute('href', '/dashboard')
  })
})
