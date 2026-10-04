import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { jsonResponse } from '../test/fixtures'
import { OrganizationListPage } from './OrganizationListPage'
import { OrganizationDetailPage } from './OrganizationDetailPage'

const rights = { can_add: true, can_change: true, can_delete: true }
const org = { id: 5, short_name: 'UNI', name: 'Université de test', admin_url: null, capabilities: rights }
const options = { organization_info_types: [{ id: 1, name: 'Téléphone', icon: 'Phone', type: 'tel' }], contact_types: [{ id: 2, name: 'Direction' }], contact_info_types: [{ id: 3, name: 'Email', icon: 'Mail', type: 'mail' }], map_provider: 'gmap' }
const orgProject = { id: 9, name: 'Visible Project', status: true, start_date: '2026-01-01', end_date: null, institutions: ['UNI', 'CHU', 'INSERM'], participants: ['Ada Reader', 'Sam Worker'], funds: ['AG · REF'], capabilities: rights, admin_url: null }
const orgContract = {
  id: 17, admin_url: '/admin/expense/contract/17/change/',
  employee: { id: 12, first_name: 'Jean', last_name: 'Dupont', can_view: true },
  contract_type: { id: 2, name: 'CDD Recherche' },
  fund: { id: 20, display_name: 'Atlas · ANR', reference: 'REF-20',
    project: { id: 3, name: 'Atlas', can_view: true, url: null },
    funder: { id: 30, name: 'Agence nationale', short_name: 'ANR', can_view: false, url: null },
    institution: { id: 40, name: 'Université', short_name: 'UL', can_view: false, url: null } },
  start_date: '2026-01-01', end_date: '2026-12-31', quotity: '0.500',
  status: { code: 'effe', label: 'Effective' }, requires_follow_up: true, is_active: true,
  temporal_state: 'current', total_amount: '25.00', capabilities: { can_change: true },
  notes: { visible_count: 2, can_add: false },
}

function mount(path: string) {
  return render(<I18nProvider><MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/organizations/institutions" element={<OrganizationListPage kind="institutions" />} />
    <Route path="/organizations/institutions/:organizationId/*" element={<OrganizationDetailPage kind="institutions" />} />
    <Route path="/organizations/funders" element={<OrganizationListPage kind="funders" />} />
    <Route path="/organizations/funders/:organizationId/*" element={<OrganizationDetailPage kind="funders" />} />
  </Routes></MemoryRouter></I18nProvider>)
}

beforeEach(() => { Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })

describe('Organization pages', () => {
  it('lists institutions with search, pagination and a create action', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.startsWith('/api/v1/organizations/institutions/?')) return jsonResponse({ count: 26, next: '/next', previous: null, results: [org], capabilities: { can_add: true } })
      throw new Error(url)
    })
    const user = userEvent.setup()
    mount('/organizations/institutions')
    expect(await screen.findByRole('link', { name: 'UNI' })).toHaveAttribute('href', '/organizations/institutions/5')
    expect(screen.getByRole('button', { name: 'Ajouter une institution' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Actions pour Université de test' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    expect(await screen.findByRole('dialog', { name: 'Modifier l’organisation' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    await user.click(screen.getByRole('button', { name: 'Actions pour Université de test' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(await screen.findByText('Supprimer cette organisation ?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    await user.type(screen.getByLabelText('Rechercher par nom ou abréviation'), 'univ')
    await user.click(screen.getByRole('button', { name: 'Rechercher' }))
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('search=univ'))).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Suivant' }))
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('offset=25'))).toBe(true)
  })

  it('lists funders without mutation controls when capabilities are absent', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ count: 1, next: null, previous: null, results: [{ ...org, capabilities: { can_add: false, can_change: false, can_delete: false } }], capabilities: { can_add: false } }))
    mount('/organizations/funders')
    expect(await screen.findByRole('link', { name: 'UNI' })).toHaveAttribute('href', '/organizations/funders/5')
    expect(screen.queryByRole('button', { name: 'Ajouter un financeur' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Université de test' })).not.toBeInTheDocument()
  })

  it('renders summary, typed information and separate lazy tabs', async () => {
    const calls: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      calls.push(url)
      if (url === '/api/v1/organizations/institutions/5/') return jsonResponse(org)
      if (url === '/api/v1/preferences/institution/5/') return jsonResponse({ favorite: false, subscription: false })
      if (url.endsWith('/options/')) return jsonResponse(options)
      if (url.endsWith('/summary/')) return jsonResponse({ projects: { total: 1, open: 1, total_amount: '100.00', available_amount: '70.00', available_amount_focus: '60.00' }, contracts: { total: 1, current: 1, active: 1, man_months: 12 } })
      if (url.endsWith('/infos/')) return jsonResponse({ items: [{ id: 7, info: options.organization_info_types[0], value: '0123456789', comment: null, admin_url: null, capabilities: rights }], capabilities: { can_add: true } })
      if (url.endsWith('/contacts/')) return jsonResponse({ items: [], capabilities: { can_add: true } })
      if (url.endsWith('/projects/')) return jsonResponse([orgProject])
      if (url.endsWith('/contracts/')) return jsonResponse([])
      if (url.startsWith('/api/v1/notes/')) return jsonResponse({ items: [], capabilities: { can_add: false } })
      throw new Error(url)
    })
    const user = userEvent.setup()
    mount('/organizations/institutions/5')
    const involvement = await screen.findByRole('heading', { name: 'Implication de l’institution' })
    const general = screen.getByRole('heading', { name: 'Informations générales' })
    const additional = await screen.findByRole('heading', { name: 'Informations complémentaires' })
    expect(general.closest('section')?.parentElement).toBe(involvement.closest('section')?.parentElement)
    expect(involvement.closest('section')?.parentElement?.nextElementSibling).toBe(additional.closest('section'))
    for (const label of ['Implication projets', 'Synthèse des contrats', 'Total projets', 'Projets ouverts', 'Montant total', 'Montant disponible', 'Montant disponible focus', 'Total contrats', 'Contrats en cours', 'Suivi RH actif', 'Mois-homme']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(await screen.findByRole('link', { name: 'Appeler: 0123456789' })).toHaveAttribute('href', 'tel:0123456789')
    expect(screen.getByRole('button', { name: 'Copier la valeur' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Actions pour Téléphone' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Modifier' }))
    expect(await screen.findByRole('dialog', { name: 'Modifier l’information' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    await user.click(screen.getByRole('button', { name: 'Actions pour Téléphone' }))
    await user.click(await screen.findByRole('menuitem', { name: 'Supprimer' }))
    expect(await screen.findByText('Supprimer cette information ?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(calls.some((url) => url.endsWith('/contacts/'))).toBe(false)
    await user.click(screen.getByRole('link', { name: 'Contacts' }))
    expect(await screen.findByText('Aucun contact.')).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Projets' }))
    expect(await screen.findByRole('link', { name: 'Visible Project' })).toHaveAttribute('href', '/projects/9')
    expect(screen.getByRole('region', { name: 'Tableau des projets, défilement horizontal' })).toBeInTheDocument()
    expect(screen.getByText('Le nom du projet ouvre sa fiche.')).toBeInTheDocument()
    expect(screen.getByText('UNI, CHU +1')).toBeInTheDocument()
    expect(screen.getByText('Ada Reader, Sam Worker')).toBeInTheDocument()
    expect(screen.getByText('AG · REF')).toBeInTheDocument()
    expect(screen.getByText('Actif')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /ajouter un projet/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Visible Project' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Visible Project' }).closest('tr')).not.toHaveAttribute('aria-selected')
    expect(screen.queryByRole('button', { name: /Modifier|Supprimer/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Notes' }))
    expect(calls.some((url) => url.startsWith('/api/v1/notes/institution/5/'))).toBe(true)
  })

  it('renders the same read-only Project table for a funder', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/organizations/funders/5/') return jsonResponse(org)
      if (url === '/api/v1/preferences/funder/5/') return jsonResponse({ favorite: false, subscription: false })
      if (url.endsWith('/projects/')) return jsonResponse([orgProject])
      throw new Error(url)
    })
    mount('/organizations/funders/5/projects')
    expect(await screen.findByRole('link', { name: 'Visible Project' })).toHaveAttribute('href', '/projects/9')
    expect(screen.getByText('UNI, CHU +1')).toBeInTheDocument()
    expect(screen.getByText('AG · REF')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Actions pour Visible Project' })).not.toBeInTheDocument()
  })

  it.each(['institutions', 'funders'])('renders the Contract Hub table without Contract mutations for %s', async (kind) => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === `/api/v1/organizations/${kind}/5/`) return jsonResponse(org)
      if (url.startsWith('/api/v1/preferences/')) return jsonResponse({ favorite: false, subscription: false })
      if (url === `/api/v1/organizations/${kind}/5/contracts/`) return jsonResponse([orgContract])
      if (url === '/api/v1/contracts/17/') return jsonResponse({ ...orgContract, capabilities: rights })
      if (url === '/api/v1/notes/contract/17/') return jsonResponse({ capabilities: { can_add: false }, items: [] })
      throw new Error(url)
    })
    const user = userEvent.setup()
    mount(`/organizations/${kind}/5/contracts`)
    const row = await screen.findByRole('row', { name: /Jean Dupont/ })
    expect(within(row).getByRole('link', { name: 'Jean Dupont' })).toHaveAttribute('href', '/employees/12')
    expect(within(row).getByRole('link', { name: 'Atlas' })).toHaveAttribute('href', '/projects/3')
    expect(row).toHaveTextContent('CDD Recherche')
    expect(row).toHaveTextContent('REF-20')
    expect(row).toHaveTextContent('25,00')
    expect(within(row).getByRole('button', { name: 'Ouvrir les notes du contrat · 2 notes' })).toHaveTextContent('2')
    expect(screen.queryByRole('button', { name: /Ajouter un contrat/ })).not.toBeInTheDocument()
    await user.click(within(row).getByText('CDD Recherche'))
    expect(await screen.findByRole('heading', { name: 'Détail du contrat' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url) === '/api/v1/contracts/17/')).toBe(true)
    await user.click(within(row).getByRole('button', { name: 'Ouvrir les notes du contrat · 2 notes' }))
    expect(await screen.findByRole('dialog', { name: 'Notes du contrat' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url) === '/api/v1/notes/contract/17/')).toBe(true)
    await user.click(within(screen.getByRole('dialog', { name: 'Notes du contrat' })).getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Notes du contrat' })).not.toBeInTheDocument())
    await user.click(within(row).getByRole('button', { name: /Actions pour Jean Dupont/ }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/expense/contract/17/change/')
    expect(screen.queryByRole('menuitem', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Supprimer' })).not.toBeInTheDocument()
  })

  it('opens a Contact Sheet with the shared typed information actions', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url === '/api/v1/organizations/institutions/5/') return jsonResponse(org)
      if (url === '/api/v1/preferences/institution/5/') return jsonResponse({ favorite: false, subscription: false })
      if (url.endsWith('/options/')) return jsonResponse(options)
      if (url.endsWith('/contacts/')) return jsonResponse({ items: [{ id: 11, first_name: 'Jane', last_name: 'Doe', type: options.contact_types[0], comment: 'Direction', admin_url: null, capabilities: rights }], capabilities: { can_add: true } })
      if (url.endsWith('/contacts/11/infos/')) return jsonResponse({ items: [{ id: 14, info: options.contact_info_types[0], value: 'jane@example.org', comment: null, admin_url: null, capabilities: rights }], capabilities: { can_add: true } })
      throw new Error(url)
    })
    const user = userEvent.setup()
    mount('/organizations/institutions/5/contacts')
    await user.click(await screen.findByRole('button', { name: /^Jane Doe/ }))
    expect(await screen.findByRole('link', { name: 'Envoyer un e-mail: jane@example.org' })).toHaveAttribute('href', 'mailto:jane@example.org')
    expect(screen.getByRole('button', { name: 'Copier la valeur' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter une information' })).toBeInTheDocument()
  })
})
