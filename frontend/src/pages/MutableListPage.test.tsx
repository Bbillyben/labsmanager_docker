import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '../i18n/I18nProvider';
import { ApiError } from '../api/errors';
import { AuthProvider } from '../auth/AuthProvider';
import { authenticatedUser, jsonResponse } from '../test/fixtures';
import { SettingsHubPage } from './SettingsHubPage';
import { MutableListGroupPage } from './MutableListPage';

const api = vi.hoisted(() => ({
  getMutableLists: vi.fn(),
  getMutableList: vi.fn(),
  createMutableItem: vi.fn(),
  updateMutableItem: vi.fn(),
  deleteMutableItem: vi.fn(),
}));
vi.mock('../api/mutableLists', () => api);

const capabilities = { can_view: true, can_add: true, can_change: true, can_delete: true };
const fields = [
  { key: 'name', label: 'Name', type: 'text', required: true, readonly: false, choices: [] },
  {
    key: 'type',
    label: 'Type',
    type: 'choice',
    required: true,
    readonly: false,
    choices: [
      { value: 'none', label: 'None' },
      { value: 'tel', label: 'Phone' },
    ],
  },
  {
    key: 'parent',
    label: 'Parent',
    type: 'relation',
    required: false,
    readonly: false,
    choices: [{ value: 2, label: 'Root' }],
  },
];
const list = {
  key: 'types',
  group: 'fund',
  label: 'Types',
  fields,
  columns: ['name', 'type'],
  capabilities,
};
const row = {
  id: 1,
  values: { name: 'Existing', type: 'none', parent: null },
  capabilities,
  editable_fields: ['name', 'type', 'parent'],
};
const groups = ['fund', 'contract', 'leaves', 'project', 'staff', 'organization', 'equipment'].map(
  (key) => ({
    key,
    label: key,
    lists: key === 'fund' ? [list] : [{ ...list, key: `${key}-types`, group: key }],
  }),
);

function renderPage(path = '/settings/lists/fund') {
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <Routes>
            <Route
              path="settings"
              element={<SettingsHubPage />}
            >
              <Route
                path="lists/:groupKey"
                element={<MutableListGroupPage />}
              />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </I18nProvider>,
  );
}

describe('MutableListPage', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(authenticatedUser));
    api.getMutableLists.mockReset().mockResolvedValue({ groups });
    api.getMutableList.mockReset().mockResolvedValue({ list, rows: [row] });
    api.createMutableItem.mockReset().mockResolvedValue(row);
    api.updateMutableItem.mockReset().mockResolvedValue(row);
    api.deleteMutableItem.mockReset().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] });
  });

  afterEach(() => vi.restoreAllMocks());

  it('manages Equipment categories and information types within LabsManager lists', async () => {
    const categoryList = {
      ...list,
      key: 'equipment-categories',
      group: 'equipment',
      label: 'Equipment categories',
      fields: [
        fields[2],
        fields[0],
        {
          key: 'is_active',
          label: 'Active',
          type: 'boolean',
          required: false,
          readonly: false,
          choices: [],
          default: true,
        },
      ],
      columns: ['name', 'is_active'],
      renderers: { name: 'tree' },
    };
    const infoList = {
      ...list,
      key: 'equipment-info-types',
      group: 'equipment',
      label: 'Types of equipment information',
    };
    api.getMutableLists.mockResolvedValue({
      groups: groups.map((group) =>
        group.key === 'equipment' ? { ...group, lists: [categoryList, infoList] } : group,
      ),
    });
    api.getMutableList.mockImplementation(async (key: string) =>
      key === 'equipment-categories'
        ? {
            list: categoryList,
            rows: [
              {
                ...row,
                values: { parent: null, name: 'Microscope', is_active: true },
                editable_fields: ['parent', 'name', 'is_active'],
                tree_level: 0,
              },
              {
                ...row,
                id: 2,
                values: { parent: 1, name: 'Child', is_active: true },
                editable_fields: ['parent', 'name', 'is_active'],
                tree_level: 1,
              },
            ],
          }
        : { list: infoList, rows: [] },
    );
    renderPage('/settings/lists/equipment');
    expect(await screen.findByRole('link', { name: 'equipment' })).toHaveAttribute(
      'href',
      '/settings/lists/equipment',
    );
    expect(await screen.findByText('Microscope')).toBeInTheDocument();
    expect(within(screen.getByRole('cell', { name: 'Child' })).getByText('└─')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Types of equipment information' }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole('button', { name: 'Ajouter' })[0]);
    expect(screen.getByRole('combobox', { name: 'Parent' })).toBeInTheDocument();
    expect(api.getMutableList).toHaveBeenCalledWith(
      'equipment-categories',
      expect.any(AbortSignal),
    );
    expect(api.getMutableList).toHaveBeenCalledWith(
      'equipment-info-types',
      expect.any(AbortSignal),
    );
  });

  it('shows backend groups and a generic compact list with create fields', async () => {
    const user = userEvent.setup();
    renderPage();
    for (const group of groups)
      expect(await screen.findByRole('link', { name: group.label })).toHaveAttribute(
        'href',
        `/settings/lists/${group.key}`,
      );
    expect(await screen.findByText('Existing')).toBeInTheDocument();
    expect(screen.getByText('None')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'New');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Type' }), 'tel');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Parent' }), '2');
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }),
    );
    expect(api.createMutableItem).toHaveBeenCalledWith('types', {
      name: 'New',
      type: 'tel',
      parent: '2',
    });
  });

  it('uses the canonical menu for edit and confirmed delete', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('Existing');
    await user.click(screen.getByRole('button', { name: 'Actions pour Existing' }));
    await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }));
    const dialog = screen.getByRole('dialog');
    await user.clear(within(dialog).getByRole('textbox', { name: 'Name' }));
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Changed');
    await user.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));
    expect(api.updateMutableItem).toHaveBeenCalledWith(
      'types',
      1,
      expect.objectContaining({ name: 'Changed' }),
    );
    await user.click(screen.getByRole('button', { name: 'Actions pour Existing' }));
    await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }));
    expect(api.deleteMutableItem).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Supprimer' }));
    expect(api.deleteMutableItem).toHaveBeenCalledWith('types', 1);
  });

  it('hides mutation controls when backend capabilities deny them', async () => {
    api.getMutableList.mockResolvedValue({
      list: { ...list, capabilities: { ...capabilities, can_add: false } },
      rows: [{ ...row, capabilities: { ...capabilities, can_change: false, can_delete: false } }],
    });
    renderPage();
    await screen.findByText('Existing');
    expect(screen.queryByRole('button', { name: 'Ajouter' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Actions pour Existing' })).not.toBeInTheDocument();
  });

  it('shows field validation returned by the backend', async () => {
    api.createMutableItem.mockRejectedValue(new ApiError(400, { name: ['Already exists.'] }));
    const user = userEvent.setup();
    renderPage();
    await screen.findByText('Existing');
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));
    await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Duplicate');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Type' }), 'tel');
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Enregistrer' }),
    );
    expect(await screen.findByText('Already exists.')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders a tree column from metadata without changing ordinary cells or values', async () => {
    const rows = [
      { ...row, id: 1, values: { ...row.values, name: 'Parent' }, tree_level: 0 },
      { ...row, id: 2, values: { ...row.values, name: 'Child' }, tree_level: 1 },
      { ...row, id: 3, values: { ...row.values, name: 'Grandchild' }, tree_level: 2 },
    ];
    api.getMutableList.mockResolvedValue({ list: { ...list, renderers: { name: 'tree' } }, rows });
    renderPage();
    const parent = await screen.findByRole('cell', { name: 'Parent' });
    const child = screen.getByRole('cell', { name: 'Child' });
    const grandchild = screen.getByRole('cell', { name: 'Grandchild' });
    expect(within(parent).queryByText('└─')).not.toBeInTheDocument();
    expect(within(child).getByText('└─')).toHaveAttribute('aria-hidden', 'true');
    expect(within(grandchild).getByText('└─')).toHaveAttribute('aria-hidden', 'true');
    expect(child.firstElementChild).toHaveStyle({ paddingInlineStart: '0.85rem' });
    expect(grandchild.firstElementChild).toHaveStyle({ paddingInlineStart: '1.7rem' });
    expect(screen.getAllByRole('cell', { name: 'None' })).toHaveLength(3);
  });
});
