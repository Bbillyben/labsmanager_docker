import { describe, expect, it } from 'vitest';
import { getPageContext } from './pageContext';

describe('topbar page context', () => {
  it('maps list, tool, settings and plugin routes to their own titles', () => {
    expect(getPageContext('/')?.label).toBe('page.home');
    expect(getPageContext('/employees/')?.label).toBe('page.employees');
    expect(getPageContext('/calendars')?.label).toBe('calendars.title');
    expect(getPageContext('/tools/import')?.label).toBe('navigation.import');
    expect(getPageContext('/tools/expenses')?.label).toBe('financial.expenses');
    expect(getPageContext('/settings/admin/plugins')?.label).toBe('settingsAdmin.plugins');
    expect(getPageContext('/plugins/Calendars/main')?.dynamic).toBe(true);
    expect(getPageContext('/unknown')).toBeNull();
  });
  it('links detail pages to their explicit parent routes', () => {
    expect(getPageContext('/employees/42/projects')?.parent).toEqual({
      label: 'page.employees',
      href: '/employees/',
    });
    expect(getPageContext('/projects/7')?.parent?.href).toBe('/projects/');
    expect(getPageContext('/equipment/8/notes')?.parent?.href).toBe('/equipment/');
    expect(getPageContext('/teams/3')?.parent?.href).toBe('/teams/');
    expect(getPageContext('/organizations/institutions/4')?.parent?.href).toBe(
      '/organizations/institutions',
    );
    expect(getPageContext('/organizations/funders/5')?.parent?.href).toBe('/organizations/funders');
  });
});
