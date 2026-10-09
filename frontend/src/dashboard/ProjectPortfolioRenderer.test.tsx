import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import type { DashboardProjectPortfolioData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { getDashboardRenderer } from './renderers'
import { ProjectPortfolioRenderer } from './ProjectPortfolioRenderer'

const data: DashboardProjectPortfolioData = {
  summary: { count: 8, active_count: 6, ending_soon_count: 2, attention_count: 3 },
  items: [
    { key: '1', name: 'NUMETAB', href: '/app/projects/1', start_date: '2026-01-01', end_date: '2027-01-01', temporal_percent: 72,
      temporal_state: 'ending_soon', financial: { amount: 100, spent: 58, percent: 58 }, financial_delta: -14,
      financial_state: { key: 'funding_behind', tone: 'neutral' },
      next_milestone: { title: 'Data integration', date: '2026-10-20', days_until: 12, relative_state: 'upcoming', href: '/app/projects/1/tasks' },
      overdue_task_count: 2, overdue_milestone_count: 1,
      attention_signals: [{ key: 'overdue_tasks', count: 2, tone: 'danger' }, { key: 'overdue_milestones', count: 1, tone: 'danger' },
        { key: 'project_ending_soon', tone: 'warning' }, { key: 'funding_behind', delta: -14, tone: 'neutral' }] },
    { key: '2', name: 'FRAME', href: '/app/projects/2', start_date: null, end_date: null, temporal_percent: null,
      temporal_state: 'unknown', financial: null, financial_delta: null, financial_state: null, next_milestone: null,
      overdue_task_count: 0, overdue_milestone_count: 0, attention_signals: [] },
  ],
}
const widget = { data } as DashboardWidget

it('shows time, finance, separate overdue counts and the next dated milestone in standard mode', () => {
  expect(getDashboardRenderer('project-portfolio')).toBe(ProjectPortfolioRenderer)
  const view = render(<I18nProvider><ProjectPortfolioRenderer widget={widget} size="standard" /></I18nProvider>)
  expect(screen.getByText('NUMETAB')).toHaveAttribute('href', '/app/projects/1')
  expect(screen.getByRole('progressbar', { name: 'Time progress for NUMETAB' })).toHaveAttribute('value', '72')
  expect(screen.getByRole('progressbar', { name: 'Financial consumption for NUMETAB' })).toHaveAttribute('value', '58')
  expect(view.container.querySelectorAll('[class*="progressGauge"]')).toHaveLength(4)
  expect(screen.getByText('Data integration')).toBeInTheDocument()
  expect(screen.getByText('2 overdue tasks')).toBeInTheDocument()
  expect(screen.getByText('1 overdue milestone')).toBeInTheDocument()
  expect(screen.getByText('Funding behind schedule')).toBeInTheDocument()
  expect(screen.getByText('20 Oct')).toBeInTheDocument()
  expect(screen.getByText(/3 need attention/)).toBeInTheDocument()
  expect(screen.queryByText('-14 pts')).not.toBeInTheDocument()
  expect(view.container.textContent).not.toMatch(/health score|\/100/)
})

it('shows a short compact warning, all explicit signals and delta when expanded or printed', () => {
  const view = render(<I18nProvider><ProjectPortfolioRenderer widget={widget} size="compact" /></I18nProvider>)
  expect(screen.queryByText('Data integration')).not.toBeInTheDocument()
  expect(screen.getByText('58%')).toBeInTheDocument()
  expect(screen.getByText('2 overdue tasks')).toBeInTheDocument()
  expect(screen.queryByText('1 overdue milestone')).not.toBeInTheDocument()
  view.rerender(<I18nProvider><ProjectPortfolioRenderer widget={widget} size="expanded" /></I18nProvider>)
  expect(screen.getByText('Data integration')).toBeInTheDocument()
  expect(screen.getByText('Project ending soon')).toBeInTheDocument()
  expect(screen.getByText('1 overdue milestone')).toBeInTheDocument()
  expect(screen.getByText('-14 pts')).toBeInTheDocument()
  view.rerender(<I18nProvider><ProjectPortfolioRenderer widget={widget} size="expanded" mode="print" /></I18nProvider>)
  expect(screen.queryByRole('link', { name: 'NUMETAB' })).not.toBeInTheDocument()
  expect(screen.getByText('1 overdue milestone')).toBeInTheDocument()
})
