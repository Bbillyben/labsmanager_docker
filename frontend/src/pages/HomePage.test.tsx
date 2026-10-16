import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser } from '../test/fixtures'
import { Sidebar } from '../layout/Sidebar'
import { HomePage } from './HomePage'

const mocks = vi.hoisted(() => ({ listDashboards: vi.fn(), listRecentItems: vi.fn(), getSystemInfo: vi.fn(), useAuth: vi.fn(), writeToClipboard: vi.fn() }))
vi.mock('../api/dashboards', () => ({ listDashboards: mocks.listDashboards }))
vi.mock('../api/recentItems', () => ({ listRecentItems: mocks.listRecentItems }))
vi.mock('../api/systemInfo', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/systemInfo')>()), getSystemInfo: mocks.getSystemInfo,
}))
vi.mock('../auth/AuthContext', () => ({ useAuth: mocks.useAuth }))
vi.mock('../utils/clipboard', () => ({ writeToClipboard: mocks.writeToClipboard }))

function showHome() {
  return render(<I18nProvider><MemoryRouter><HomePage /></MemoryRouter></I18nProvider>)
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  mocks.listDashboards.mockReset()
  mocks.listRecentItems.mockReset()
  mocks.getSystemInfo.mockReset().mockResolvedValue({
    system_info: { labsmanager_version: 'react-phase1-rc4', python_version: '3.11.9', django_version: '5.1',
      database: { vendor: 'postgresql', version: '13.17' } }, help_links: [],
  })
  mocks.useAuth.mockReset()
  mocks.writeToClipboard.mockReset().mockResolvedValue(true)
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

  it('uses the same navigation cards and sidebar icons for all five quick links', async () => {
    const user = { ...authenticatedUser, capabilities: { ...authenticatedUser.capabilities, view_team_list: true } }
    mocks.useAuth.mockReturnValue({ status: 'authenticated', user })
    mocks.listRecentItems.mockResolvedValue([
      { url_id: 'fund', obj_id: 130, type: 'fund', title: 'ANR-42', subtitle: 'Atlas', icon: 'PiggyBank', url: '/app/projects/98/funding#fund-row-130', last_viewed_at: '' },
    ])
    render(<I18nProvider><MemoryRouter><Sidebar expanded interactive onRequestExpand={() => {}} user={user} /><HomePage /></MemoryRouter></I18nProvider>)
    const resume = await screen.findByRole('region', { name: 'Reprendre' })
    const quick = screen.getByRole('region', { name: 'Accès rapides' })
    const navigation = screen.getByRole('navigation', { name: 'Navigation principale' })
    fireEvent.click(within(navigation).getByRole('button', { name: 'Outils' }))
    const expected = [
      ['Calendriers', '/calendars'], ['Projets', '/projects/'], ['Employés', '/employees/'],
      ['Équipes', '/teams/'], ['Explorateur de fonds', '/tools/fund-items'],
    ] as const
    expect(within(quick).getAllByRole('link').map((link) => link.textContent)).toEqual(expected.map(([label]) => label))
    const recentCard = within(resume).getByRole('link', { name: /ANR-42/ })
    for (const [label, href] of expected) {
      const card = within(quick).getByRole('link', { name: label })
      const sidebarLink = within(navigation).getByRole('link', { name: label })
      expect(card).toHaveAttribute('href', href)
      expect(card.querySelectorAll('svg')).toHaveLength(2)
      expect(card.querySelector('svg')?.getAttribute('class')).toBe(sidebarLink.querySelector('svg')?.getAttribute('class'))
      expect(card.parentElement?.parentElement?.className).toBe(recentCard.parentElement?.parentElement?.className)
      expect(card.querySelector('small')).not.toBeInTheDocument()
    }
    expect(recentCard).toHaveAttribute('href', '/projects/98/funding#fund-row-130')
    expect(recentCard).toHaveTextContent('Atlas')
  })

  it('sends first-time users to the existing dashboard onboarding', async () => {
    mocks.listDashboards.mockResolvedValue([])
    showHome()
    expect(await screen.findByRole('link', { name: /Créer mon tableau de bord/ })).toHaveAttribute('href', '/dashboard')
  })

  it('shows configured help links and copies issue diagnostics with the backend version', async () => {
    mocks.getSystemInfo.mockResolvedValue({
      system_info: { labsmanager_version: 'v4.3.0', python_version: '3.11.9', django_version: '5.1',
        database: { vendor: 'postgresql', version: '13.17' } },
      help_links: [{ label: 'Documentation', url: 'https://example.test/docs' }, { label: 'Erreurs', url: 'https://example.test/issues' }],
    })
    showHome()
    const help = await screen.findByRole('region', { name: 'Aide et support' })
    const documentation = await within(help).findByRole('link', { name: 'Documentation' })
    const issues = within(help).getByRole('link', { name: 'Erreurs' })
    expect(documentation.parentElement?.parentElement?.className).toBe(
      within(screen.getByRole('region', { name: 'Accès rapides' })).getByRole('link', { name: 'Calendriers' }).parentElement?.parentElement?.className,
    )
    expect(documentation).toHaveAttribute('href', 'https://example.test/docs')
    expect(issues).toHaveAttribute('href', 'https://example.test/issues')
    for (const card of [documentation, issues]) {
      expect(card).toHaveAttribute('target', '_blank')
      expect(card).toHaveAttribute('rel', 'noopener noreferrer')
      expect(card.querySelectorAll('svg')).toHaveLength(2)
      expect(card.querySelector('small')).not.toBeInTheDocument()
    }
    expect(documentation.querySelector('svg')).toHaveClass('lucide-book-open')
    expect(issues.querySelector('svg')).toHaveClass('lucide-bug')
    expect(within(help).getByText('Version v4.3.0')).toBeInTheDocument()
    fireEvent.click(within(help).getByRole('button', { name: 'Copier les informations techniques' }))
    await screen.findByText('Informations techniques copiées.')
    const copied = String(mocks.writeToClipboard.mock.calls[0][0])
    expect(copied).toContain('LabsManager system information\nlabsmanager_version: v4.3.0')
    expect(copied).toContain('python_version: 3.11.9')
    expect(copied).toContain('django_version: 5.1')
    expect(copied).toContain('database: postgresql 13.17')
    expect(copied).toContain('URL:')
    expect(copied).toContain('Browser:')
    expect(copied).toContain('Language:')
    expect(copied).toContain('Theme: light')
    expect(copied).toMatch(/Timestamp: \d{4}-\d\d-\d\dT/)
    expect(copied).not.toContain('undefined')
    expect(copied).not.toContain('\n\n')
  })

  it('omits unavailable runtime details from the copied text', async () => {
    mocks.getSystemInfo.mockResolvedValue({
      system_info: { labsmanager_version: 'react-phase1-rc4', python_version: '', django_version: '5.1',
        database: { vendor: 'sqlite', version: null } }, help_links: [],
    })
    showHome()
    await screen.findByText('Version react-phase1-rc4')
    fireEvent.click(screen.getByRole('button', { name: 'Copier les informations techniques' }))
    await screen.findByText('Informations techniques copiées.')
    const copied = String(mocks.writeToClipboard.mock.calls[0][0])
    expect(copied).toContain('database: sqlite')
    expect(copied).not.toContain('python_version:')
    expect(copied).not.toContain('null')
    expect(copied).not.toContain('\n\n')
  })
})
