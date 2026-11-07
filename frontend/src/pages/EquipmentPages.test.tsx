import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n/I18nProvider';
import { jsonResponse } from '../test/fixtures';
import { EquipmentDetailPage } from './EquipmentDetailPage';
import { EquipmentCreatePage, EquipmentListPage } from './EquipmentListPage';

const capabilities = { can_view: true, can_add: true, can_change: true, can_delete: true };
const category = { id: 2, name: 'Microscopes', is_active: true };
const equipment = {
  id: 7,
  admin_url: null,
  name: 'Zeiss Scope',
  internal_reference: 'EQ-7',
  category,
  current_responsibles: [],
  current_institutions: [],
  status: 'in_service',
  status_label: 'In service',
  acquisition_date: null,
  commissioning_date: null,
  decommissioning_date: null,
  capabilities,
};
const collection = (items: unknown[]) => ({
  items,
  capabilities: { can_add: true, can_change: true, can_delete: true },
});

function renderAt(path: string) {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/equipment/"
            element={<EquipmentListPage />}
          />
          <Route
            path="/equipment/new"
            element={<EquipmentCreatePage />}
          />
          <Route
            path="/equipment/:equipmentId"
            element={<EquipmentDetailPage />}
          />
          <Route
            path="/equipment/:equipmentId/:section"
            element={<EquipmentDetailPage />}
          />
        </Routes>
      </MemoryRouter>
    </I18nProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('Equipment pages', () => {
  it('shows every current manager and keeps responsible and institution filters in the URL', async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      if (url === '/api/v1/equipment/categories/') return jsonResponse(collection([category]));
      if (url.startsWith('/api/v1/equipment/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              ...equipment,
              current_responsibles: [
                { id: 4, name: 'Ada Lovelace' },
                { id: 5, name: 'Grace Hopper' },
              ],
              current_institutions: [{ id: 3, name: 'LAB' }],
            },
          ],
          capabilities,
        });
      if (url === '/api/v1/employees/4/')
        return jsonResponse({ id: 4, first_name: 'Ada', last_name: 'Lovelace' });
      if (url === '/api/v1/equipment/institution-options/?id=3')
        return jsonResponse({
          results: [{ id: 3, short_name: 'LAB', name: 'Laboratory' }],
          has_more: false,
        });
      throw new Error(url);
    });
    renderAt('/equipment/?responsible=4&institution=3');
    expect(await screen.findByRole('link', { name: 'Ada Lovelace' })).toHaveAttribute(
      'href',
      '/employees/4',
    );
    expect(screen.getByRole('link', { name: 'Grace Hopper' })).toHaveAttribute(
      'href',
      '/employees/5',
    );
    expect(screen.getByRole('link', { name: 'LAB' })).toHaveAttribute(
      'href',
      '/organizations/institutions/3',
    );
    expect(
      requests.some((url) => url.includes('responsible=4') && url.includes('institution=3')),
    ).toBe(true);
  });
  it('loads a server page and keeps search and pagination on the server', async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      if (url === '/api/v1/equipment/categories/') return jsonResponse(collection([category]));
      if (url.startsWith('/api/v1/equipment/?')) {
        const offset = new URL(url, 'http://localhost').searchParams.get('offset');
        return jsonResponse({
          count: 30,
          next: offset === '25' ? null : 'next',
          previous: offset === '25' ? 'previous' : null,
          results: [equipment],
          capabilities,
        });
      }
      throw new Error(url);
    });
    renderAt('/equipment/');
    expect(await screen.findByRole('link', { name: 'Zeiss Scope' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(requests.some((url) => url.includes('offset=25'))).toBe(true));
    await userEvent.type(screen.getByRole('textbox', { name: 'Name or reference' }), 'EQ-7');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    await waitFor(() =>
      expect(requests.some((url) => url.includes('search=EQ-7') && url.includes('offset=0'))).toBe(
        true,
      ),
    );
  });

  it('creates an equipment through the shared Sheet and opens its detail', async () => {
    const writes: string[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === '/api/v1/equipment/capabilities/') return jsonResponse(capabilities);
      if (url === '/api/v1/equipment/categories/') return jsonResponse(collection([category]));
      if (url === '/api/v1/equipment/' && init?.method === 'POST') {
        writes.push(String(init.body));
        return jsonResponse(equipment, 201);
      }
      if (url === '/api/v1/equipment/7/') return jsonResponse(equipment);
      if (url === '/api/v1/preferences/equipment/7/')
        return jsonResponse({ favorite: false, subscription: false });
      if (
        url === '/api/v1/equipment/7/generic-info/' ||
        url === '/api/v1/equipment/7/responsibilities/' ||
        url === '/api/v1/equipment/7/institutions/'
      )
        return jsonResponse(collection([]));
      throw new Error(url);
    });
    renderAt('/equipment/new');
    expect(await screen.findByRole('heading', { name: 'Add equipment' })).toBeInTheDocument();
    await userEvent.type(screen.getByRole('textbox', { name: 'Name' }), 'Zeiss Scope');
    await userEvent.type(screen.getByRole('textbox', { name: 'Internal reference' }), 'EQ-7');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Category' }), '2');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('heading', { name: 'Zeiss Scope' })).toBeInTheDocument();
    expect(writes[0]).toContain('"internal_reference":"EQ-7"');
  });

  it('shows the relation history and hides identities withheld by the API', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url === '/api/v1/equipment/7/')
        return jsonResponse({ ...equipment, capabilities: { ...capabilities, can_delete: false } });
      if (url === '/api/v1/preferences/equipment/7/')
        return jsonResponse({ favorite: false, subscription: false });
      if (url === '/api/v1/equipment/7/generic-info/') return jsonResponse(collection([]));
      if (url === '/api/v1/equipment/7/responsibilities/')
        return jsonResponse(
          collection([
            {
              id: 1,
              employee: { id: 4, name: 'Ada Lovelace', is_active: false, can_view: true },
              start_date: '2024-01-01',
              end_date: null,
              is_active: true,
            },
            {
              id: 2,
              employee: { id: null, name: null, is_active: null, can_view: false },
              start_date: '2023-01-01',
              end_date: '2023-12-31',
              is_active: false,
            },
          ]),
        );
      if (url === '/api/v1/equipment/7/institutions/')
        return jsonResponse(
          collection([
            {
              id: 3,
              institution: { id: null, short_name: null, name: null, can_view: false },
              inventory_number: 'INV-42',
              start_date: null,
              end_date: '2023-12-31',
              status: 'closed',
              status_label: 'Closed',
              is_active: false,
            },
          ]),
        );
      throw new Error(url);
    });
    renderAt('/equipment/7');
    expect(await screen.findByRole('link', { name: 'Ada Lovelace' })).toHaveAttribute(
      'href',
      '/employees/4',
    );
    expect(screen.getByLabelText('Overview').children).toHaveLength(3);
    expect(screen.getAllByText('Identity unavailable')).toHaveLength(1);
    expect(await screen.findByText(/INV-42/)).toBeInTheDocument();
    const previous = screen.getByRole('button', { name: '↳ 1 previous' });
    expect(previous).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(previous);
    expect(screen.getAllByText('Identity unavailable')).toHaveLength(2);
    expect(screen.getByRole('button', { name: '↟ Collapse' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    await userEvent.click(screen.getByRole('button', { name: '↟ Collapse' }));
    expect(screen.getAllByText('Identity unavailable')).toHaveLength(1);
    expect(screen.queryByRole('link', { name: 'Identity unavailable' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
  });

  it('shows preferences followed by permitted actions and persists both toggles', async () => {
    let state = { favorite: false, subscription: false };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === '/api/v1/equipment/7/') return jsonResponse(equipment);
      if (url === '/api/v1/preferences/equipment/7/') {
        if (init?.method === 'PUT') state = { ...state, ...JSON.parse(String(init.body)) };
        return jsonResponse(state);
      }
      if (
        url === '/api/v1/equipment/7/generic-info/' ||
        url === '/api/v1/equipment/7/responsibilities/' ||
        url === '/api/v1/equipment/7/institutions/'
      )
        return jsonResponse(collection([]));
      throw new Error(url);
    });
    renderAt('/equipment/7');
    const favorite = await screen.findByRole('button', { name: 'Add to favorites' });
    const bell = screen.getByRole('button', { name: 'Subscribe' });
    const menu = screen.getByRole('button', { name: 'Actions for Zeiss Scope' });
    expect(favorite.compareDocumentPosition(bell) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(bell.compareDocumentPosition(menu) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await userEvent.click(favorite);
    expect(await screen.findByRole('button', { name: 'Remove from favorites' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Subscribe' }));
    expect(await screen.findByRole('button', { name: 'Unsubscribe' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(menu);
    expect(await screen.findByRole('menuitem', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.queryByText(/Export|PDF|Word/)).not.toBeInTheDocument();
  });

  it('keeps preferences available without showing an empty action menu', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url === '/api/v1/equipment/7/')
        return jsonResponse({
          ...equipment,
          capabilities: { ...capabilities, can_change: false, can_delete: false },
        });
      if (url === '/api/v1/preferences/equipment/7/')
        return jsonResponse({ favorite: false, subscription: false });
      if (
        url === '/api/v1/equipment/7/generic-info/' ||
        url === '/api/v1/equipment/7/responsibilities/' ||
        url === '/api/v1/equipment/7/institutions/'
      )
        return jsonResponse(collection([]));
      throw new Error(url);
    });
    renderAt('/equipment/7');
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Add to favorites' })).toBeEnabled(),
    );
    expect(screen.getByRole('button', { name: 'Subscribe' })).toBeEnabled();
    expect(
      screen.queryByRole('button', { name: 'Actions for Zeiss Scope' }),
    ).not.toBeInTheDocument();
  });

  it('opens the shared report dialog only for permitted Equipment formats', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url === '/api/v1/equipment/7/')
        return jsonResponse({
          ...equipment,
          capabilities: { ...capabilities, can_export_word: true, can_export_pdf: false },
        });
      if (url === '/api/v1/preferences/equipment/7/')
        return jsonResponse({ favorite: false, subscription: false });
      if (url === '/api/v1/reports/equipment/7/word/')
        return jsonResponse({ templates: [{ id: 3, name: 'Equipment template' }] });
      if (
        url === '/api/v1/equipment/7/generic-info/' ||
        url === '/api/v1/equipment/7/responsibilities/' ||
        url === '/api/v1/equipment/7/institutions/'
      )
        return jsonResponse(collection([]));
      throw new Error(url);
    });
    renderAt('/equipment/7');
    await userEvent.click(await screen.findByRole('button', { name: 'Actions for Zeiss Scope' }));
    const wordAction = await screen.findByRole('menuitem', { name: 'Export Word' });
    expect(screen.queryByRole('menuitem', { name: 'Export PDF' })).not.toBeInTheDocument();
    await userEvent.click(wordAction);
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Equipment template')).toBeInTheDocument();
  });

  it('shows linked expenses across Funds and keeps unlink distinct from financial deletion', async () => {
    const writes: string[] = [];
    let linked = true;
    const expense = {
      id: 19,
      expense_id: 'EQ-19',
      desc: 'Service',
      date: '2026-03-01',
      type: { id: 5, short_name: 'EQ', name: 'Equipment' },
      amount: '42.00',
      status: 'r',
      contract: null,
      budget: null,
      fund: { id: 3, name: 'Fund A' },
      nature: 'maintenance',
      capabilities: { can_change: true, can_delete: true },
      link_capabilities: { can_change: true, can_unlink: true },
      can_view_business_assignments: true,
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === '/api/v1/equipment/7/') return jsonResponse(equipment);
      if (url === '/api/v1/preferences/equipment/7/')
        return jsonResponse({ favorite: false, subscription: false });
      if (url.startsWith('/api/v1/equipment/7/expenses/?'))
        return jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [expense],
          total_visible: '42.00',
          capabilities: {
            expense_mode: 'e',
            can_add: true,
            can_link: true,
            can_sync_expenses: false,
          },
        });
      if (url === '/api/v1/equipment/7/expenses/options/')
        return jsonResponse({
          cost_types: [expense.type],
          hr_type_ids: [],
          funds: [{ id: 3, name: 'Fund A', expense_mode: 'e' }],
          contracts: [],
          budgets: [],
        });
      if (url === '/api/v1/expenses/19/business-assignments/' && init?.method === 'GET')
        return jsonResponse({
          equipment: linked
            ? {
                equipment: { id: 7, name: 'Zeiss Scope', internal_reference: 'EQ-7' },
                nature: 'maintenance',
              }
            : null,
          capabilities: { can_link: !linked, can_change: linked, can_unlink: linked },
        });
      if (url === '/api/v1/expenses/19/business-assignments/' && init?.method === 'DELETE') {
        writes.push(url);
        linked = false;
        return new Response(null, { status: 204 });
      }
      throw new Error(url);
    });
    renderAt('/equipment/7/expenses');
    expect(await screen.findByText('EQ-19')).toBeInTheDocument();
    expect(screen.getByText('Fund A')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
    expect(screen.getByText(/Total of visible linked expenses/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Link existing expense' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Actions for EQ-19' }));
    expect(
      await screen.findByRole('menuitem', { name: 'Business assignments…' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Delete expense' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('menuitem', { name: 'Business assignments…' }));
    expect(await screen.findByText('Linked equipment')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Unlink equipment' }));
    await userEvent.click(
      within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Unlink equipment' }),
    );
    await waitFor(() => expect(writes).toEqual(['/api/v1/expenses/19/business-assignments/']));
  });

  it('reports a denied list without exposing Equipment data', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url === '/api/v1/equipment/categories/') return jsonResponse({}, 403);
      if (url.startsWith('/api/v1/equipment/?')) return jsonResponse({}, 403);
      throw new Error(url);
    });
    renderAt('/equipment/');
    expect(await screen.findByText('You cannot view equipment.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Zeiss Scope' })).not.toBeInTheDocument();
  });
});
