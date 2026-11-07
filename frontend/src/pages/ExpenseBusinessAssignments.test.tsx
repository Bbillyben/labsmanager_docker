import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n/I18nProvider';
import { jsonResponse } from '../test/fixtures';
import { ExpenseBusinessAssignments } from './ExpenseBusinessAssignments';

const equipment = { id: 7, name: 'Scope', internal_reference: 'EQ-7' };

function renderPanel(onChanged = vi.fn()) {
  render(
    <I18nProvider>
      <MemoryRouter>
        <ExpenseBusinessAssignments
          expenseId={19}
          returnFocus={{ current: null }}
          onClose={vi.fn()}
          onChanged={onChanged}
        />
      </MemoryRouter>
    </I18nProvider>,
  );
  return onChanged;
}

afterEach(() => vi.restoreAllMocks());

describe('Expense business assignments', () => {
  it('searches visible Equipment, links it, then changes only the business nature', async () => {
    let nature: string | null = null;
    const writes: Array<{ method: string; body: Record<string, unknown> }> = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (url === '/api/v1/expenses/19/business-assignments/' && method === 'GET')
        return jsonResponse({
          equipment: nature ? { equipment, nature } : null,
          capabilities: {
            can_link: !nature,
            can_change: Boolean(nature),
            can_unlink: Boolean(nature),
          },
        });
      if (url.startsWith('/api/v1/equipment/?'))
        return jsonResponse({ count: 1, next: null, previous: null, results: [equipment] });
      if (url === '/api/v1/equipment/7/') return jsonResponse(equipment);
      if (
        url === '/api/v1/expenses/19/business-assignments/' &&
        (method === 'POST' || method === 'PATCH')
      ) {
        const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
        writes.push({ method, body });
        nature = String(body.nature);
        return jsonResponse({ equipment, nature }, method === 'POST' ? 201 : 200);
      }
      throw new Error(url);
    });
    const changed = renderPanel();
    expect(await screen.findByText('No business assignment.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Link to equipment' }));
    await userEvent.type(screen.getByRole('combobox', { name: 'Equipment' }), 'Scope');
    await userEvent.click(await screen.findByRole('option', { name: 'Scope · EQ-7' }));
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Expense purpose' }),
      'purchase',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('link', { name: 'Scope · EQ-7' })).toHaveAttribute(
      'href',
      '/equipment/7',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Change nature' }));
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Expense purpose' }),
      'repair',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(2));
    expect(writes).toEqual([
      { method: 'POST', body: { equipment_id: 7, nature: 'purchase' } },
      { method: 'PATCH', body: { nature: 'repair' } },
    ]);
  });

  it('keeps read-only associations visible without mutation controls', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input) === '/api/v1/expenses/19/business-assignments/')
        return jsonResponse({
          equipment: { equipment, nature: 'maintenance' },
          capabilities: { can_link: false, can_change: false, can_unlink: false },
        });
      throw new Error(String(input));
    });
    renderPanel();
    expect(await screen.findByRole('link', { name: 'Scope · EQ-7' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Change equipment' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Unlink equipment' })).not.toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByText('Linked equipment')).toBeInTheDocument();
  });

  it('replaces the Equipment through server search without changing financial fields', async () => {
    const replacement = { id: 8, name: 'New Scope', internal_reference: 'EQ-8' };
    let linked = equipment;
    const writes: Record<string, unknown>[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === '/api/v1/expenses/19/business-assignments/' && init?.method === 'GET')
        return jsonResponse({
          equipment: { equipment: linked, nature: 'maintenance' },
          capabilities: { can_link: false, can_change: true, can_unlink: true },
        });
      if (url.startsWith('/api/v1/equipment/?'))
        return jsonResponse({ count: 1, next: null, previous: null, results: [replacement] });
      if (url === '/api/v1/equipment/7/') return jsonResponse(equipment);
      if (url === '/api/v1/equipment/8/') return jsonResponse(replacement);
      if (url === '/api/v1/expenses/19/business-assignments/' && init?.method === 'PATCH') {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        writes.push(body);
        linked = replacement;
        return jsonResponse({ equipment: linked, nature: 'maintenance' });
      }
      throw new Error(url);
    });
    renderPanel();
    expect(await screen.findByRole('link', { name: 'Scope · EQ-7' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Change equipment' }));
    await userEvent.type(screen.getByRole('combobox', { name: 'Equipment' }), 'New');
    await userEvent.click(await screen.findByRole('option', { name: 'New Scope · EQ-8' }));
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('link', { name: 'New Scope · EQ-8' })).toBeInTheDocument();
    expect(writes).toEqual([{ equipment_id: 8, nature: 'maintenance' }]);
  });

  it('reports a failed assignment read and leaves the panel open for retry', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ detail: 'Unavailable' }, 503));
    renderPanel();
    expect(await screen.findByText('Could not load business assignments.')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
