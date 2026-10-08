import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import type { DashboardEmployeeWorkloadData, DashboardWidget } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { EmployeeWorkloadRenderer } from './EmployeeWorkloadRenderer'
import { getDashboardRenderer } from './renderers'

const single: DashboardEmployeeWorkloadData = { mode: 'single', employee: { id: 1, name: 'Alice Martin', href: '/app/employees/1' }, metrics: [
  { key: 'project_allocation', value: 130, unit: 'percent', reference_value: 100 },
  { key: 'open_tasks', value: 6, unit: 'count', reference_value: null },
  { key: 'open_milestones', value: 2, unit: 'count', reference_value: null },
  { key: 'open_work_items', value: 8, unit: 'count', reference_value: null },
] }
const comparison: DashboardEmployeeWorkloadData = { mode: 'comparison', metric: 'open_tasks', unit: 'count', reference_value: null, items: [
  { employee_id: 2, employee_name: 'Bob Dupont', value: 8, href: '/app/employees/2' },
  { employee_id: 1, employee_name: 'Alice Martin', value: 6, href: '/app/employees/1' },
] }

it('shows all four metrics for one employee with a 100% allocation reference only', () => {
  expect(getDashboardRenderer('employee-workload')).toBe(EmployeeWorkloadRenderer)
  const view = render(<I18nProvider><EmployeeWorkloadRenderer widget={{ data: single } as DashboardWidget} size="compact" /></I18nProvider>)
  expect(screen.getByRole('link', { name: 'Alice Martin' })).toHaveAttribute('href', '/app/employees/1')
  expect(screen.getByText('130%')).toBeInTheDocument()
  expect(screen.getByText('Open tasks')).toBeInTheDocument()
  expect(screen.getByText('Open milestones')).toBeInTheDocument()
  expect(screen.getByText('Open work items')).toBeInTheDocument()
  expect(view.container.querySelectorAll('[aria-label="100% reference"]')).toHaveLength(1)
  view.rerender(<I18nProvider><EmployeeWorkloadRenderer widget={{ data: single } as DashboardWidget} size="expanded" mode="print" /></I18nProvider>)
  expect(screen.queryByRole('link', { name: 'Alice Martin' })).not.toBeInTheDocument()
})

it('compares one metric per employee without an artificial count threshold', () => {
  const view = render(<I18nProvider><EmployeeWorkloadRenderer widget={{ data: comparison } as DashboardWidget} size="standard" mode="presentation" /></I18nProvider>)
  expect(screen.getByRole('link', { name: 'Bob Dupont' })).toHaveAttribute('href', '/app/employees/2')
  expect(screen.getAllByRole('img')).toHaveLength(2)
  expect(view.container.querySelector('[aria-label="100% reference"]')).toBeNull()
  expect(view.container.textContent?.indexOf('Bob Dupont')).toBeLessThan(view.container.textContent?.indexOf('Alice Martin') ?? 0)
  const allocation: DashboardEmployeeWorkloadData = { ...comparison, metric: 'project_allocation', unit: 'percent', reference_value: 100 }
  view.rerender(<I18nProvider><EmployeeWorkloadRenderer widget={{ data: allocation } as DashboardWidget} size="expanded" /></I18nProvider>)
  expect(view.container.querySelectorAll('[aria-label="100% reference"]')).toHaveLength(2)
})
