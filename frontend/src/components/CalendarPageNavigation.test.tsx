import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getUIPages, type UIContribution } from '../api/uiContributions'
import { I18nProvider } from '../i18n/I18nProvider'
import { CalendarPageNavigation } from './CalendarPageNavigation'

vi.mock('../api/uiContributions', async (original) => ({
  ...(await original<typeof import('../api/uiContributions')>()), getUIPages: vi.fn(),
}))

const page = (id: string, order = 0): UIContribution => ({
  id: `plugin:demo:${id}`, plugin_slug: 'demo', local_id: id, slot: 'plugin.page', type: 'page',
  label: 'Fallback', icon: null, behavior: null, confirm: false, priority: 0,
  navigation: { location: 'calendars', labels: { fr: 'Agenda', en: 'Calendar' }, icon: 'calendar', order },
})

function Location() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}{location.search}</output>
}

function NativeRoute() {
  const location = useLocation()
  const navigate = useNavigate()
  const tab = new URLSearchParams(location.search).get('tab') === 'projects' ? 'projects' : 'employees'
  return <CalendarPageNavigation active={tab} onSelectNative={(next) => navigate(`/calendars?tab=${next}`)} />
}

function HistoryButtons() {
  const navigate = useNavigate()
  return <><button onClick={() => navigate(-1)}>Previous page</button><button onClick={() => navigate(1)}>Next page</button></>
}

function renderAt(path = '/calendars') {
  return render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/calendars" element={<NativeRoute />} />
    <Route path="/plugins/:slug/:page" element={<CalendarPageNavigation active="plugin:demo:calendar" />} />
  </Routes><Location /><HistoryButtons /></MemoryRouter></I18nProvider>)
}

describe('calendar page navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [] })
  })

  it('keeps both native choices without plugin pages and discovers only once per mount', async () => {
    renderAt()
    expect(screen.getByRole('button', { name: 'Calendrier général' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Calendrier des projets' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.queryByRole('link', { name: 'Agenda' })).not.toBeInTheDocument()
    expect(getUIPages).toHaveBeenCalledTimes(1)
  })

  it('sorts visible plugin pages and navigates in both directions', async () => {
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [page('later', 3), page('calendar', 0)] })
    const user = userEvent.setup()
    renderAt('/calendars?tab=projects')
    expect(await screen.findAllByRole('link', { name: 'Agenda' })).toHaveLength(2)
    const links = screen.getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(['Agenda', 'Agenda'])
    expect(screen.getByRole('button', { name: 'Calendrier des projets' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getAllByRole('link', { name: 'Agenda' })[0])
    expect(screen.getByTestId('location')).toHaveTextContent('/plugins/demo/calendar')
    expect(screen.getAllByRole('link', { name: 'Agenda' })[0]).toHaveAttribute('aria-current', 'page')
    await user.click(screen.getByRole('link', { name: 'Calendrier général' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/calendars?tab=employees')
    expect(screen.getByRole('button', { name: 'Calendrier général' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(screen.getByRole('button', { name: 'Previous page' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/plugins/demo/calendar')
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/calendars?tab=employees')
  })

  it('keeps plugin choices visible during navigation while refreshing their list', async () => {
    vi.mocked(getUIPages).mockResolvedValueOnce({ contributions: [page('calendar')] })
      .mockReturnValueOnce(new Promise(() => {}))
    const user = userEvent.setup()
    renderAt('/calendars?tab=employees')
    await user.click(await screen.findByRole('link', { name: 'Agenda' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/plugins/demo/calendar')
    expect(screen.getByRole('link', { name: 'Agenda' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Calendrier général' })).toBeInTheDocument()
  })

  it('uses the active language and falls back to the page label', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    vi.mocked(getUIPages).mockResolvedValue({ contributions: [page('calendar'), { ...page('fallback'), navigation: { ...page('fallback').navigation!, labels: {} } }] })
    renderAt()
    expect(await screen.findByRole('link', { name: 'Calendar' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Fallback' })).toBeInTheDocument()
  })
})
