import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CalendarEvent } from '../api/employees';
import { AuthContext, type AuthContextValue } from '../auth/AuthContext';
import { I18nProvider } from '../i18n/I18nProvider';
import { authenticatedUser, jsonResponse } from '../test/fixtures';
import { EquipmentMaintenanceCalendarPage } from './EquipmentMaintenanceCalendarPage';
import { EquipmentMaintenanceSection } from './EquipmentMaintenanceSection';
import { GlobalCalendarsPage } from './GlobalCalendarsPage';

vi.mock('../calendar/SharedCalendar', () => ({
  SharedCalendar: ({
    events,
    onOpen,
  }: {
    events: CalendarEvent[];
    onOpen: (event: CalendarEvent) => void;
  }) => <button onClick={() => onOpen(events[0])}>Open calendar event</button>,
}));

const capabilities = { can_view: true, can_add: true, can_change: true, can_delete: true };
const calendarAuth: AuthContextValue = {
  status: 'authenticated',
  user: {
    ...authenticatedUser,
    capabilities: { ...authenticatedUser.capabilities, view_equipment_maintenance: true },
  },
  refresh: async () => {},
  markUnauthenticated: () => {},
  changeTheme: async () => {
    throw new Error('Not used in this test');
  },
};
const maintenance = {
  id: 9,
  equipment: { id: 7, name: 'Scope' },
  title: 'Inspect optics',
  maintenance_type: 'inspection',
  status: 'planned',
  scheduled_date: '2026-05-12',
  scheduled_start_time: null,
  scheduled_end_time: null,
  performed_date: null,
  description: 'Check lenses',
  report: '',
  expense_link: null,
  capabilities,
};

function renderAt(path: string) {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/equipment/:equipmentId/maintenance"
            element={<EquipmentMaintenanceSection equipmentId="7" />}
          />
          <Route
            path="/calendars"
            element={
              <AuthContext.Provider value={calendarAuth}>
                <GlobalCalendarsPage />
              </AuthContext.Provider>
            }
          />
          <Route
            path="/equipment/:equipmentId/maintenance-calendar"
            element={<EquipmentMaintenanceCalendarPage />}
          />
        </Routes>
      </MemoryRouter>
    </I18nProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('Equipment maintenance', () => {
  it('shows planned records and protects read-only actions', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/equipment/maintenances/9/') return jsonResponse(maintenance);
      if (String(input).startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              ...maintenance,
              capabilities: { ...capabilities, can_change: false, can_delete: false },
            },
          ],
          capabilities: { ...capabilities, can_add: false },
        });
      throw new Error(String(input));
    });
    renderAt('/equipment/7/maintenance');
    expect(await screen.findByText('Inspect optics')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Inspect optics/ }));
    expect(await screen.findByText('Check lenses')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Schedule maintenance' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Actions for Inspect optics' }),
    ).not.toBeInTheDocument();
  });

  it('creates a maintenance without a financial Expense', async () => {
    let saved = false;
    const writes: unknown[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: saved ? 1 : 0,
          next: null,
          previous: null,
          results: saved ? [maintenance] : [],
          capabilities,
        });
      if (url === '/api/v1/equipment/7/maintenances/expense-options/') return jsonResponse([]);
      if (url === '/api/v1/equipment/7/maintenances/' && init?.method === 'POST') {
        writes.push(JSON.parse(String(init.body)));
        saved = true;
        return jsonResponse(maintenance, 201);
      }
      throw new Error(url);
    });
    renderAt('/equipment/7/maintenance');
    await userEvent.click(await screen.findByRole('button', { name: 'Schedule maintenance' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Title' }), 'Inspect optics');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ title: 'Inspect optics', expense_link_id: null });
    expect(await screen.findByText('Inspect optics')).toBeInTheDocument();
  });

  it('edits a maintenance with an authorized Expense', async () => {
    let current = { ...maintenance };
    const writes: Array<{ method: string; body: Record<string, unknown> }> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [current],
          capabilities,
        });
      if (url === '/api/v1/equipment/7/maintenances/expense-options/')
        return jsonResponse([{ id: 4, label: 'Expense 4' }]);
      if (url === '/api/v1/equipment/maintenances/9/' && init?.method === 'GET')
        return jsonResponse(current);
      if (url === '/api/v1/equipment/maintenances/9/' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body));
        writes.push({ method: 'PATCH', body });
        current = {
          ...current,
          title: body.title,
          expense_link: { id: 4, expense_id: 22, label: 'Expense 4' },
        };
        return jsonResponse(current);
      }
      throw new Error(url);
    });
    renderAt('/equipment/7/maintenance');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Actions for Inspect optics' }),
    );
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Edit' }));
    await userEvent.clear(screen.getByRole('textbox', { name: 'Title' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Title' }), 'Recalibrate optics');
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Associated expense' }),
      '4',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() =>
      expect(writes[0]).toMatchObject({
        method: 'PATCH',
        body: { title: 'Recalibrate optics', expense_link_id: 4 },
      }),
    );
    expect(await screen.findByText('Recalibrate optics')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /^Recalibrate optics/ }));
    expect(await screen.findByText('Associated expense: Expense 4')).toBeInTheDocument();
  });

  it('records completion and keeps the intervention in history', async () => {
    let current = { ...maintenance };
    const writes: Record<string, unknown>[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [current],
          capabilities,
        });
      if (url === '/api/v1/equipment/maintenances/9/complete/' && init?.method === 'POST') {
        const body = JSON.parse(String(init.body));
        writes.push(body);
        current = {
          ...current,
          status: 'completed',
          performed_date: body.performed_date,
          report: body.report,
        };
        return jsonResponse(current);
      }
      throw new Error(url);
    });
    renderAt('/equipment/7/maintenance');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Actions for Inspect optics' }),
    );
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Mark completed' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Maintenance report' }), 'Done');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(writes[0]).toMatchObject({ report: 'Done' }));
    expect(writes[0].performed_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(await screen.findByRole('heading', { name: /Completed/ })).toBeInTheDocument();
  });

  it('cancels a planned maintenance and keeps it in the history', async () => {
    let current = { ...maintenance };
    const writes: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [current],
          capabilities,
        });
      if (url === '/api/v1/equipment/maintenances/9/cancel/' && init?.method === 'POST') {
        writes.push(url);
        current = { ...current, status: 'cancelled' };
        return jsonResponse(current);
      }
      throw new Error(url);
    });
    renderAt('/equipment/7/maintenance');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Actions for Inspect optics' }),
    );
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Cancel maintenance' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(await screen.findByText('Inspect optics')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Cancelled/ })).toBeInTheDocument();
  });

  it('opens a selected maintenance from the dedicated global calendar', async () => {
    const event = {
      id: 'equipment-maintenance:9',
      title: 'Inspect optics',
      start: '2026-05-12',
      end: '2026-05-13',
      source: 'core',
      kind: 'equipment-maintenance',
      all_day: true,
      color: null,
      description: null,
      display: 'auto',
      metadata: { maintenance_id: 9, equipment_id: 7, status: 'planned' },
    };
    const requests: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      if (url.startsWith('/api/v1/equipment/maintenances/calendar/?'))
        return jsonResponse({ events: [event], capabilities });
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [maintenance],
          capabilities,
        });
      if (url === '/api/v1/equipment/maintenances/9/') return jsonResponse(maintenance);
      throw new Error(url);
    });
    renderAt('/calendars?tab=maintenance&date=2026-05-12');
    await userEvent.click(await screen.findByRole('button', { name: 'Open calendar event' }));
    expect(await screen.findByRole('dialog', { name: 'Inspect optics' })).toBeInTheDocument();
    expect(requests.some((url) => url.includes('/api/v1/equipment/maintenances/9/'))).toBe(true);
  });

  it('switches the Equipment section between list and its scoped calendar', async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      if (url.startsWith('/api/v1/equipment/7/maintenances/calendar/?'))
        return jsonResponse({
          events: [
            {
              id: 'equipment-maintenance:9',
              title: 'Inspect optics',
              metadata: { equipment_id: 7, maintenance_id: 9 },
            },
          ],
          capabilities,
        });
      if (url.startsWith('/api/v1/equipment/7/maintenances/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [maintenance],
          capabilities,
        });
      if (url === '/api/v1/equipment/maintenances/9/') return jsonResponse(maintenance);
      throw new Error(url);
    });
    renderAt('/equipment/7/maintenance?date=2026-05-12&maintenanceStatus=planned');
    expect(await screen.findByText('Inspect optics')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Maintenance calendar' }));
    expect(await screen.findByRole('button', { name: 'Open calendar event' })).toBeInTheDocument();
    expect(screen.queryByText('Inspect optics')).not.toBeInTheDocument();
    expect(
      requests.some((url) => url.startsWith('/api/v1/equipment/7/maintenances/calendar/?')),
    ).toBe(true);
    expect(
      requests.some(
        (url) => url.includes('/maintenances/calendar/?') && url.includes('status=planned'),
      ),
    ).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'List' }));
    expect(await screen.findByText('Inspect optics')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Maintenance calendar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Open calendar event' }));
    expect(await screen.findByRole('dialog', { name: 'Inspect optics' })).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(screen.getByRole('button', { name: 'List' })).toHaveAttribute('aria-pressed', 'true');
  });
});
