import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import type { DashboardCatalog, DashboardSource } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { DashboardWidgetEditor } from './DashboardWidgetEditor'

const source: DashboardSource = { key: 'core.employee-workload', label: 'Employee workload', description: '', category: 'HR',
  compatible_renderers: ['employee-workload'], default_renderer: 'employee-workload', allow_multiple: true,
  config_fields: { scope: { type: 'choice', choices: ['single', 'team', 'subordinates'], default: 'single' },
    employee_id: { type: 'employee' }, team_id: { type: 'team' },
    metric: { type: 'choice', choices: ['project_allocation', 'open_tasks'], default: 'project_allocation' },
    limit: { type: 'integer', default: 5 } } }
const catalog: DashboardCatalog = { scope: 'user', definitions: [], sources: [source],
  renderers: { 'employee-workload': { label: 'Employee workload', config_fields: {} } },
  employee_options: [{ id: 1, name: 'Alice Martin' }], team_options: [{ id: 2, name: 'Team A' }] }

it('shows only the target needed by the current scope and keeps metric in the sidebar', async () => {
  const user = userEvent.setup()
  const onSave = vi.fn()
  render(<I18nProvider><DashboardWidgetEditor source={source} catalog={catalog} pending={false} onCancel={() => {}} onSave={onSave} /></I18nProvider>)
  expect(screen.getByLabelText('Employee')).toBeInTheDocument()
  expect(screen.queryByLabelText('Team')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Metric')).not.toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Employee'), '1')
  await user.selectOptions(screen.getByLabelText('Scope'), 'team')
  expect(screen.queryByLabelText('Employee')).not.toBeInTheDocument()
  expect(screen.getByLabelText('Team')).toBeInTheDocument()
  expect(screen.getByLabelText('Metric')).toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Team'), '2')
  await user.selectOptions(screen.getByLabelText('Metric'), 'open_tasks')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  expect(onSave).toHaveBeenCalledWith('employee-workload', '', expect.objectContaining({ scope: 'team', team_id: 2, metric: 'open_tasks' }))
  expect(onSave.mock.calls[0][2]).not.toHaveProperty('employee_id')
})
