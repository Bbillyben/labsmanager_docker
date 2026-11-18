import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { listEquipment, type EquipmentList } from '../api/equipment';
import { listEquipmentMaintenances, type MaintenanceCollection } from '../api/equipmentMaintenance';
import { AuthContext } from '../auth/AuthContext';
import { I18nProvider } from '../i18n/I18nProvider';
import { authenticatedUser } from '../test/fixtures';
import { EmployeeDetailContext } from './employeeDetailContext';
import { EmployeeEquipment } from './EmployeeEquipment';

vi.mock('../api/equipment', () => ({ listEquipment: vi.fn() }));
vi.mock('../api/equipmentMaintenance', () => ({ listEquipmentMaintenances: vi.fn() }));

const equipment = (id: number, name: string) => ({
  id,
  name,
  internal_reference: `EQ-${id}`,
  category: { name: 'Microscope' },
  status: 'in_service',
  responsibility_start_date: '2026-01-01',
  current_inventories: [],
});
const equipmentList = (items: ReturnType<typeof equipment>[]) =>
  ({
    count: items.length,
    next: null,
    previous: null,
    results: items,
  }) as EquipmentList;
const maintenanceList = (id: number) =>
  ({
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id,
        title: `Intervention ${id}`,
        maintenance_type: 'preventive',
        status: 'planned',
        scheduled_date: '2026-12-01',
        performed_date: null,
        description: 'Contrôle prévu',
        report: '',
      },
    ],
  }) as MaintenanceCollection;

function LocationProbe() {
  return <span data-testid="location">{useLocation().pathname}</span>;
}

function renderPanel(canViewEquipment = true, canViewMaintenance = true) {
  const user = {
    ...authenticatedUser,
    capabilities: {
      ...authenticatedUser.capabilities,
      view_equipment_list: canViewEquipment,
      view_equipment_maintenance: canViewMaintenance,
    },
  };
  return render(
    <MemoryRouter initialEntries={['/employees/12/equipment']}>
      <AuthContext.Provider
        value={{
          status: 'authenticated',
          user,
          refresh: vi.fn(),
          markUnauthenticated: vi.fn(),
          changeTheme: vi.fn(),
        }}
      >
        <I18nProvider>
          <EmployeeDetailContext.Provider value={{ employee: {} as never, employeeId: '12' }}>
            <EmployeeEquipment />
            <LocationProbe />
          </EmployeeDetailContext.Provider>
        </I18nProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe('Employee Equipment tab', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] });
    vi.mocked(listEquipment).mockReset();
    vi.mocked(listEquipmentMaintenances).mockReset();
    vi.mocked(listEquipment).mockResolvedValue(
      equipmentList([
        {
          ...equipment(1, 'Scope A'),
          current_inventories: [{ institution: 'LAB', inventory_number: 'LAB-42' }],
        },
        equipment(2, 'Scope B'),
      ]),
    );
    vi.mocked(listEquipmentMaintenances).mockImplementation(async (id) =>
      maintenanceList(Number(id)),
    );
  });

  it('filters on the server, opens one maintenance history, and keeps the Equipment link independent', async () => {
    const user = userEvent.setup();
    renderPanel();
    const first = await screen.findByRole('row', { name: /Scope A/ });
    expect(vi.mocked(listEquipment).mock.calls[0][0]).toContain('responsible=12');
    expect(first).toHaveTextContent('LAB · LAB-42');
    await user.click(within(first).getByRole('link', { name: 'Scope A' }));
    expect(screen.getByTestId('location')).toHaveTextContent('/equipment/1');
    expect(listEquipmentMaintenances).not.toHaveBeenCalled();

    await user.click(first);
    expect(await screen.findByText('Intervention 1')).toBeInTheDocument();
    expect(first).toHaveAttribute('data-selected', 'true');
    expect(screen.getByText('Contrôle prévu')).toBeInTheDocument();
    await user.click(first);
    expect(screen.queryByText('Intervention 1')).not.toBeInTheDocument();
    await user.click(first);
    await screen.findByText('Intervention 1');
    await user.click(screen.getByRole('row', { name: /Scope B/ }));
    expect(await screen.findByText('Intervention 2')).toBeInTheDocument();
    expect(screen.queryByText('Intervention 1')).not.toBeInTheDocument();
    expect(listEquipmentMaintenances).toHaveBeenCalledWith(
      '2',
      expect.any(String),
      expect.any(AbortSignal),
    );
  });

  it('keeps the Equipment list without exposing maintenance when its permission is absent', async () => {
    const user = userEvent.setup();
    renderPanel(true, false);
    const first = await screen.findByRole('row', { name: /Scope A/ });
    await user.click(first);
    expect(listEquipmentMaintenances).not.toHaveBeenCalled();
  });

  it('allows retrying a maintenance error and paging through its history', async () => {
    const user = userEvent.setup();
    vi.mocked(listEquipmentMaintenances)
      .mockRejectedValueOnce(new Error('Unavailable'))
      .mockResolvedValueOnce({ ...maintenanceList(1), next: '/next' })
      .mockResolvedValueOnce(maintenanceList(3));
    renderPanel();
    await user.click(await screen.findByRole('row', { name: /Scope A/ }));
    expect(await screen.findByText('Impossible de charger les maintenances.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Réessayer' }));
    expect(await screen.findByText('Intervention 1')).toBeInTheDocument();
    const detailRow = screen.getByText('Intervention 1').closest('tr')!;
    await user.click(within(detailRow).getByRole('button', { name: 'Suivant' }));
    expect(await screen.findByText('Intervention 3')).toBeInTheDocument();
    expect(vi.mocked(listEquipmentMaintenances).mock.calls[2][1]).toContain('offset=25');
  });

  it('does not fetch without Equipment permission', () => {
    renderPanel(false);
    expect(screen.getByText('Vous ne pouvez pas consulter les équipements.')).toBeInTheDocument();
    expect(listEquipment).not.toHaveBeenCalled();
  });

  it('shows empty and error states', async () => {
    vi.mocked(listEquipment).mockResolvedValueOnce(equipmentList([]));
    const empty = renderPanel();
    expect(
      await screen.findByText(
        'Aucun équipement actuellement sous la responsabilité de cet employé.',
      ),
    ).toBeInTheDocument();
    empty.unmount();
    vi.mocked(listEquipment).mockRejectedValueOnce(new Error('Unavailable'));
    renderPanel();
    expect(await screen.findByText('Impossible de charger les équipements.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument();
  });
});
