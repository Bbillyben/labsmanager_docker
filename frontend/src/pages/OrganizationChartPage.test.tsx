import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { OrganizationChart } from '../api/organizationChart'
import { I18nProvider } from '../i18n/I18nProvider'
import { ApiError } from '../api/errors'

const { getChart, setScope, setCenter, paneMouseDown, paneClick } = vi.hoisted(() => ({
  getChart: vi.fn(), setScope: vi.fn(), setCenter: vi.fn(), paneMouseDown: vi.fn(), paneClick: vi.fn(),
}))
vi.mock('../api/organizationChart', () => ({ getOrganizationChart: getChart, setOrganizationChartScope: setScope }))
vi.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => children,
  useReactFlow: () => ({ fitView: vi.fn(), setCenter }),
  ReactFlow: ({ nodes, edges, nodeTypes }: { nodes: { id: string; data: unknown }[]; edges: unknown[]; nodeTypes: Record<string, React.ComponentType<{ data: unknown }>> }) => {
    const Employee = nodeTypes.employee
    return <div data-testid="chart" data-edges={edges.length} onMouseDown={paneMouseDown} onClick={paneClick}>{nodes.map((node) => <Employee key={node.id} data={node.data} />)}</div>
  },
  Handle: () => null,
  Background: () => null,
  Controls: () => null,
  Position: { Top: 'top', Bottom: 'bottom' },
}))
vi.mock('./organizationLayout', () => ({
  NODE_WIDTH: 220, NODE_HEIGHT: 88,
  layoutOrganizationGraph: async (graph: { employees: { id: number }[]; relationships: unknown[] }) => ({
    nodes: graph.employees.map((employee) => ({ id: String(employee.id), position: { x: employee.id * 220, y: 0 }, data: { employee } })),
    edges: graph.relationships,
  }),
}))

import { OrganizationChartPage } from './OrganizationChartPage'

const chart: OrganizationChart = {
  show_current_only: true,
  employees: [
    { id: 1, name: 'Ada Root', is_active: true, statuses: [{ code: 'ENG', name: 'Engineer' }], can_view: true },
    { id: 2, name: 'Bea Child', is_active: true, statuses: [], can_view: true },
  ],
  relationships: [{ superior_id: 1, employee_id: 2 }],
}

function LocationPath() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}</output>
}

function renderPage() {
  return render(<I18nProvider><MemoryRouter><OrganizationChartPage /><LocationPath /></MemoryRouter></I18nProvider>)
}

describe('OrganizationChartPage', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    getChart.mockReset().mockResolvedValue(chart)
    setScope.mockReset().mockResolvedValue({ show_current_only: false })
    setCenter.mockReset()
    paneMouseDown.mockReset()
    paneClick.mockReset()
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { callback(0); return 1 })
  })

  it('shows one employee node, link, status and a real expand control', async () => {
    const user = userEvent.setup()
    renderPage()
    expect(await screen.findByRole('link', { name: 'Ada Root' })).toHaveAttribute('href', '/employees/1')
    expect(screen.getByText('Engineer')).toBeInTheDocument()
    expect(screen.getByTestId('chart')).toHaveAttribute('data-edges', '1')
    await user.click(screen.getByRole('button', { name: /Replier Ada Root/ }))
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Bea Child' })).not.toBeInTheDocument())
    expect(screen.getByTestId('location')).toHaveTextContent('/')
    expect(paneMouseDown).not.toHaveBeenCalled()
    expect(paneClick).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: /Développer Ada Root/ }))
    expect(await screen.findByRole('link', { name: 'Bea Child' })).toBeInTheDocument()
  })

  it('searches and focuses a match, and persists current-only preference', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByRole('link', { name: 'Ada Root' })
    await user.type(screen.getByPlaceholderText('Rechercher un employé'), 'bea')
    await user.click(screen.getByRole('button', { name: 'Bea Child' }))
    expect(setCenter).toHaveBeenCalled()
    await user.click(screen.getByRole('checkbox', { name: 'Afficher uniquement l’organisation actuelle' }))
    expect(setScope).toHaveBeenCalledWith(false)
    await waitFor(() => expect(getChart).toHaveBeenCalledTimes(2))
  })

  it('shows a controlled message for cyclic hierarchy data', async () => {
    getChart.mockRejectedValue(new ApiError(409, { detail: 'hierarchy_cycle' }))
    renderPage()
    expect(await screen.findByText(/Un cycle dans les relations hiérarchiques/)).toBeInTheDocument()
  })

  it('keeps inactive and isolated nodes interactive, while honoring can_view', async () => {
    const user = userEvent.setup()
    getChart.mockResolvedValue({ ...chart, employees: [
      ...chart.employees,
      { id: 3, name: 'Cid Former', is_active: false, statuses: [], can_view: true },
      { id: 4, name: 'Dee Isolated', is_active: true, statuses: [], can_view: true },
      { id: 5, name: 'Eve Hidden Link', is_active: true, statuses: [], can_view: false },
    ], relationships: [...chart.relationships, { superior_id: 2, employee_id: 3 }] })
    renderPage()
    expect(await screen.findByRole('link', { name: 'Cid Former' })).toHaveAttribute('href', '/employees/3')
    expect(screen.getByRole('link', { name: 'Cid Former' }).closest('[data-inactive]')).toHaveAttribute('data-inactive', 'true')
    expect(screen.getByText('Dee Isolated').closest('[data-isolated]')).toHaveAttribute('data-isolated', 'true')
    expect(screen.queryByRole('link', { name: 'Eve Hidden Link' })).not.toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('Rechercher un employé'), 'dee')
    await user.click(screen.getByRole('button', { name: 'Dee Isolated' }))
    expect(setCenter).toHaveBeenCalled()
    await user.clear(screen.getByPlaceholderText('Rechercher un employé'))
    await user.type(screen.getByPlaceholderText('Rechercher un employé'), 'cid')
    await user.click(screen.getByRole('button', { name: 'Cid Former' }))
    expect(setCenter).toHaveBeenCalledTimes(2)
  })

  it('renders match, ancestor and descendant with separate priority', async () => {
    const user = userEvent.setup()
    getChart.mockResolvedValue({ ...chart, employees: [
      ...chart.employees,
      { id: 3, name: 'Cid Descendant', is_active: true, statuses: [], can_view: true },
    ], relationships: [...chart.relationships, { superior_id: 2, employee_id: 3 }] })
    renderPage()
    await screen.findByRole('link', { name: 'Cid Descendant' })
    await user.type(screen.getByPlaceholderText('Rechercher un employé'), 'bea')
    expect(screen.getByRole('link', { name: 'Ada Root' }).closest('[data-highlight]')).toHaveAttribute('data-highlight', 'ancestor')
    expect(screen.getByRole('link', { name: 'Bea Child' }).closest('[data-highlight]')).toHaveAttribute('data-highlight', 'match')
    expect(screen.getByRole('link', { name: 'Cid Descendant' }).closest('[data-highlight]')).toHaveAttribute('data-highlight', 'descendant')
  })
})
