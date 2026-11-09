import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { I18nProvider } from '../i18n/I18nProvider';
import { PageHeader } from '../ui/PageHeader';
import { usePageTitle, usePageTitleContext } from './PageTitleContext';
import { PageTitleProvider } from './PageTitleProvider';

function CurrentTitle() {
  return <output data-testid="current-title">{usePageTitleContext()?.title}</output>;
}

function PluginTitle() {
  usePageTitle('Team calendar', { href: '/calendars', label: 'Calendriers' });
  const context = usePageTitleContext();
  return (
    <output>
      {context?.parent?.label} › {context?.title}
    </output>
  );
}

describe('shared page titles', () => {
  it('uses a detail name already loaded by the page and keeps it in the content', async () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={['/employees/42']}>
          <PageTitleProvider>
            <CurrentTitle />
            <PageHeader title="Ada Lovelace" />
          </PageTitleProvider>
        </MemoryRouter>
      </I18nProvider>,
    );
    expect(await screen.findByText('Ada Lovelace', { selector: 'output' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Ada Lovelace', level: 2 })).toBeInTheDocument();
  });

  it('removes a generic page title from the content when the app bar owns it', () => {
    render(
      <I18nProvider>
        <MemoryRouter initialEntries={['/tools/import']}>
          <PageTitleProvider>
            <PageHeader title="Import" />
          </PageTitleProvider>
        </MemoryRouter>
      </I18nProvider>,
    );
    expect(screen.queryByRole('heading', { name: 'Import' })).not.toBeInTheDocument();
  });

  it('accepts a plugin page title and parent through the shared contract', async () => {
    render(
      <MemoryRouter initialEntries={['/plugins/Calendars/main']}>
        <PageTitleProvider>
          <PluginTitle />
        </PageTitleProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText('Calendriers › Team calendar')).toBeInTheDocument();
  });
});
