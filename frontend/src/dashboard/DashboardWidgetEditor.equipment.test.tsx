import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { DashboardCatalog, DashboardSource } from '../api/dashboards';
import { I18nProvider } from '../i18n/I18nProvider';
import { DashboardWidgetEditor } from './DashboardWidgetEditor';

it('configures the Equipment maintenance KPI with the standard scope and integer fields', async () => {
  const source: DashboardSource = {
    key: 'core.upcoming-maintenance',
    label: 'Upcoming maintenance',
    description: 'Open interventions',
    category: 'Equipment',
    compatible_renderers: ['kpi'],
    default_renderer: 'kpi',
    allow_multiple: true,
    config_fields: {
      scope: { type: 'choice', choices: ['all_visible', 'mine'], default: 'all_visible' },
      within_days: { type: 'integer', default: 30, min: 1, max: 365 },
    },
  };
  const catalog: DashboardCatalog = {
    scope: 'user',
    definitions: [],
    sources: [source],
    renderers: { kpi: { label: 'Indicator', config_fields: {} } },
  };
  const onSave = vi.fn();
  const user = userEvent.setup();
  render(
    <I18nProvider>
      <DashboardWidgetEditor
        source={source}
        catalog={catalog}
        pending={false}
        onCancel={() => {}}
        onSave={onSave}
      />
    </I18nProvider>,
  );
  expect(screen.getByLabelText('Within')).toHaveValue(30);
  await user.selectOptions(screen.getByLabelText('Scope'), 'mine');
  await user.clear(screen.getByLabelText('Within'));
  await user.type(screen.getByLabelText('Within'), '14');
  await user.click(screen.getByRole('button', { name: 'Save' }));
  expect(onSave).toHaveBeenCalledWith('kpi', '', { scope: 'mine', within_days: 14 });
});
