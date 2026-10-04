import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { DashboardPresentation } from './DashboardPresentation'

const api = vi.hoisted(() => ({ getDashboard: vi.fn(), getDashboardCatalog: vi.fn() }))
vi.mock('../api/dashboards', () => api)
vi.mock('./DashboardGrid', () => ({ DashboardGrid: ({ widgets, mode }: { widgets: { id: string; data: { value: number } }[]; mode: string }) => <div data-testid="presentation-grid" data-mode={mode}>{widgets.map((item) => <span key={item.id}>{item.data.value}</span>)}</div> }))

function renderAt(path: string) {
  return render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes><Route path="dashboard/:dashboardId/present" element={<DashboardPresentation />} /><Route path="dashboard" element={<p>Returned dashboard</p>} /></Routes></MemoryRouter></I18nProvider>)
}

beforeEach(() => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
  api.getDashboard.mockReset(); api.getDashboardCatalog.mockReset()
})

describe('Dashboard presentation', () => {
  it('loads the same owned detail endpoint in read-only mode and returns to the selected dashboard', async () => {
    api.getDashboard.mockResolvedValue({ id: 7, name: 'Visible dashboard', scope: 'user', widgets: [{ id: 'one', data: { value: 42 } }] })
    api.getDashboardCatalog.mockResolvedValue({ definitions: [] })
    renderAt('/dashboard/7/present')
    expect(await screen.findByTestId('presentation-grid')).toHaveAttribute('data-mode', 'presentation')
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Visible dashboard' })).toBeInTheDocument()
    expect(api.getDashboard).toHaveBeenCalledWith(7)
    await userEvent.setup().click(screen.getByRole('link', { name: 'Quitter la présentation' }))
    expect(screen.getByText('Returned dashboard')).toBeInTheDocument()
  })

  it('does not render a dashboard refused by the owner-scoped API', async () => {
    api.getDashboard.mockRejectedValue(new Error('404'))
    api.getDashboardCatalog.mockResolvedValue({ definitions: [] })
    renderAt('/dashboard/8/present')
    await waitFor(() => expect(screen.getByText('Impossible de charger les tableaux de bord.')).toBeInTheDocument())
    expect(screen.queryByTestId('presentation-grid')).not.toBeInTheDocument()
  })
})
