import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import type { DashboardProjectHealthBarsData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { ProjectHealthBarsRenderer } from './ProjectHealthBarsRenderer'
import { getDashboardRenderer } from './renderers'

const data: DashboardProjectHealthBarsData = { summary: { count: 1, active_count: 1, ending_soon_count: 1, attention_count: 1 }, items: [{
  key: '1', name: 'NUMETAB', href: '/app/projects/1',
  milestones: { total: 12, upcoming_count: 7, imminent_count: 3, overdue_count: 2, unscheduled_count: 0 },
  tasks: { total: 18, upcoming_count: 12, imminent_count: 3, overdue_count: 3, unscheduled_count: 0 },
  contracts: { total: 9, active_count: 6, ending_soon_count: 2, expired_rh_active_count: 1 },
  funding: { amount: 100, spent: 112, percent: 112, tone: 'danger' },
  deadline: { percent: 83, state: 'ending_soon', tone: 'warning', relative: { state: 'ends_in', count: 4, unit: 'months' } },
  funding_pace: { applicable: true, ratio: 1.35, state: 'above', tone: 'warning' },
}] }
const widget = { data } as DashboardWidget

it('registers the graphic renderer and shows three metrics plus three gauges in compact mode', () => {
  expect(getDashboardRenderer('project-health-bars')).toBe(ProjectHealthBarsRenderer)
  render(<I18nProvider><ProjectHealthBarsRenderer widget={widget} size="compact" /></I18nProvider>)
  expect(screen.getByRole('link', { name: 'NUMETAB' })).toHaveAttribute('href', '/app/projects/1')
  expect(screen.getByRole('img', { name: /12 Milestones: 7 upcoming, 3 imminent, 2 overdue/ })).toBeInTheDocument()
  expect(screen.getByRole('img', { name: /18 Tasks: 12 upcoming, 3 imminent, 3 overdue/ })).toBeInTheDocument()
  expect(screen.getByRole('img', { name: /9 Contracts: 6 current HR follow-up, 2 ending soon, 1 expired/ })).toBeInTheDocument()
  expect(screen.getByRole('progressbar', { name: 'Funding consumption' })).toHaveAttribute('value', '100')
  expect(screen.getByRole('progressbar', { name: 'Project deadline' })).toHaveAttribute('value', '83')
  expect(screen.getByRole('img', { name: /Funding pace: 1.35; target 1.0: 1/ })).toBeInTheDocument()
  expect(screen.getByText('112%')).toBeInTheDocument()
})

it('shows segment details when expanded and preserves values in presentation and print', () => {
  const view = render(<I18nProvider><ProjectHealthBarsRenderer widget={widget} size="standard" /></I18nProvider>)
  expect(screen.getByText('Ends in 4 months')).toBeInTheDocument()
  expect(screen.getByText('2 ending soon · 1 HR attention')).toBeInTheDocument()
  expect(screen.queryByText('7 upcoming')).not.toBeInTheDocument()
  view.rerender(<I18nProvider><ProjectHealthBarsRenderer widget={widget} size="expanded" mode="presentation" /></I18nProvider>)
  expect(screen.getByText('7 upcoming')).toBeInTheDocument()
  expect(screen.getByText('112 spent / 100 planned')).toBeInTheDocument()
  view.rerender(<I18nProvider><ProjectHealthBarsRenderer widget={widget} size="compact" mode="print" /></I18nProvider>)
  expect(screen.getByText('7 upcoming')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'NUMETAB' })).not.toBeInTheDocument()
})

it('keeps every Project and its graphics at each size while varying card detail', () => {
  const projects = ['NUMETAB', 'MIGAD', 'PreciseIT', 'Long Project Name Without Spaces That Must Wrap'].map((name, index) => ({
    ...data.items[0], key: String(index + 1), name, href: `/app/projects/${index + 1}`,
  }))
  const multiple = { data: { ...data, items: projects } } as DashboardWidget
  const view = render(<I18nProvider><ProjectHealthBarsRenderer widget={multiple} size="compact" /></I18nProvider>)

  for (const size of ['compact', 'standard', 'expanded'] as const) {
    view.rerender(<I18nProvider><ProjectHealthBarsRenderer widget={multiple} size={size} /></I18nProvider>)
    const cards = screen.getAllByRole('listitem')
    expect(cards).toHaveLength(projects.length)
    cards.forEach((card, index) => {
      const content = within(card)
      expect(content.getByRole('link', { name: projects[index].name })).toHaveAttribute('href', projects[index].href)
      expect(content.getByText('Ending soon')).toBeInTheDocument()
      expect(content.getAllByRole('img')).toHaveLength(4) // Three stacked metrics and the pace gauge.
      expect(content.getAllByRole('progressbar')).toHaveLength(2) // Funding and deadline.
      expect(content.getByText('112%')).toBeInTheDocument()
      expect(content.getByText('Ends in 4 months')).toBeInTheDocument()
      if (size === 'expanded') expect(content.getByText('7 upcoming')).toBeInTheDocument()
      else expect(content.queryByText('7 upcoming')).not.toBeInTheDocument()
    })
  }
})
