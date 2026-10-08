import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import type { DashboardCatalog, DashboardSource } from '../api/dashboards'
import { I18nProvider } from '../i18n/I18nProvider'
import { DashboardWidgetEditor } from './DashboardWidgetEditor'

const source: DashboardSource = {
  key: 'core.timeline', label: 'Timeline', description: 'Shared timeline', category: 'Work',
  compatible_renderers: ['timeline-calendar', 'calendar-grid'], default_renderer: 'timeline-calendar', allow_multiple: true,
  config_fields: {
    include_tasks: { type: 'boolean', default: true, group: 'sources' },
    include_milestones: { type: 'boolean', default: true, group: 'sources' },
    calendar_days: { type: 'choice', choices: ['7', '14', '21', '30', '60'], default: '14', group: 'horizon' },
    tasks_project_scope: { type: 'choice', choices: ['context', 'all_visible', 'specific_project'], group: 'tasks' },
    tasks_project_id: { type: 'project', group: 'tasks' },
    tasks_scope: { type: 'choice', choices: ['all_visible', 'mine'], default: 'mine', group: 'tasks' },
    milestones_project_scope: { type: 'choice', choices: ['context', 'all_visible', 'specific_project'], group: 'milestones' },
    milestones_project_id: { type: 'project', group: 'milestones' },
    milestones_status: { type: 'choice', choices: ['all', 'open', 'done'], default: 'open', group: 'milestones' },
  },
}
const catalog: DashboardCatalog = { scope: 'user', sources: [source], definitions: [], renderers: { 'timeline-calendar': { label: 'Timeline calendar', config_fields: {} }, 'calendar-grid': { label: 'Calendar grid', config_fields: {} } }, project_options: [{ id: 3, name: 'NUMETAB' }] }

it('groups provider settings and saves independent project scopes', async () => {
  const user = userEvent.setup()
  const onSave = vi.fn()
  render(<I18nProvider><DashboardWidgetEditor source={source} catalog={catalog} pending={false} onCancel={() => {}} onSave={onSave} /></I18nProvider>)
  expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Horizon' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Tasks' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Milestones' })).toBeInTheDocument()
  await user.selectOptions(screen.getByLabelText('Project scope', { selector: '#dashboard-field-tasks_project_scope' }), 'specific_project')
  await user.selectOptions(screen.getByLabelText('Project', { selector: '#dashboard-field-tasks_project_id' }), '3')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  expect(onSave).toHaveBeenCalledWith('timeline-calendar', '', expect.objectContaining({ tasks_project_scope: 'specific_project', tasks_project_id: 3, milestones_project_scope: 'all_visible' }))
})

it('offers the calendar grid while keeping the detailed timeline as default', async () => {
  const user = userEvent.setup()
  const onSave = vi.fn()
  render(<I18nProvider><DashboardWidgetEditor source={source} catalog={catalog} pending={false} onCancel={() => {}} onSave={onSave} /></I18nProvider>)
  const select = screen.getByLabelText('Display')
  expect(select).toHaveValue('timeline-calendar')
  expect(screen.getByRole('option', { name: 'Calendar grid' })).toBeInTheDocument()
  await user.selectOptions(select, 'calendar-grid')
  await user.click(screen.getByRole('button', { name: 'Save' }))
  expect(onSave).toHaveBeenCalledWith('calendar-grid', '', expect.any(Object))
})
