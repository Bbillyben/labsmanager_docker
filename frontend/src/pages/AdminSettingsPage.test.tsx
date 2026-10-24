import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import { I18nProvider } from '../i18n/I18nProvider'
import { authenticatedUser, jsonResponse } from '../test/fixtures'
import { AppRouter } from '../router/AppRouter'

function renderAt(path: string, staff = true, invitationError = false, canAssignGroups = false, pluginError = false, pluginHold?: Promise<void>) {
  window.history.pushState({}, '', path)
  const account = { ...authenticatedUser, is_staff: staff }
  const calls: string[] = []
  let invitationRows = [
    { id: 1, email: 'active@example.test', created: '2026-10-01T10:00:00Z', sent: '2026-10-01T10:01:00Z', accepted: false, key_expired: false, inviter: { id: 7, username: 'ada' } },
    { id: 2, email: 'expired@example.test', created: '2026-09-01T10:00:00Z', sent: '2026-09-01T10:01:00Z', accepted: true, key_expired: true, inviter: null },
  ]
  let plugins = [
    { key: 'sample', human_name: 'Sample', description: 'Sample plugin', author: 'Ada', pub_date: null, version: '1', website: null, license: null, mixins: ['settings', 'schedule', 'urls'], active: true, is_builtin: false, origin: 'sample', error: false },
    { key: 'sifacexpenseimport', human_name: 'SifacExpenseImport', description: 'Import plugin', author: 'Ada', pub_date: null, version: '1', website: null, license: null, mixins: ['import'], active: false, is_builtin: false, origin: 'external', error: false },
    { key: 'internal', human_name: 'Internal', description: '', author: '', pub_date: null, version: null, website: null, license: null, mixins: [], active: true, is_builtin: true, origin: 'builtin', error: false },
  ]
  let dependencyState = 'missing'
  const dependencies = () => ({ key: 'broken', human_name: 'Broken plugin', state: dependencyState, requirements: [{ name: 'icalendar', required: '==7.3.0', installed_version: null, on_disk_version: null, state: 'missing' }], errors: [], restart_required: false, can_install: dependencyState === 'missing', operation: dependencyState === 'queued' ? { state: 'queued', message: 'Installation queued.' } : null })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    calls.push(`${init?.method ?? 'GET'} ${url}`)
    if (url === '/api/v1/me/') return jsonResponse(account)
    if (url === '/api/v1/settings/lists/') return jsonResponse({ groups: [] })
    if (url === '/api/v1/settings/user/stale/') return jsonResponse({ settings: [] })
    if (url === '/api/v1/settings/admin/general/settings/' && init?.method === 'GET') return jsonResponse({ settings: [{ key: 'MAIL_OBJECT_PREFIX', name: 'Mail Object Prefix', description: '', type: 'string', value: '[LabsManager]', default: '[LabsManager]', choices: [], can_change: true }] })
    if (url === '/api/v1/settings/admin/general/settings/MAIL_OBJECT_PREFIX/' && init?.method === 'PATCH') return jsonResponse({ key: 'MAIL_OBJECT_PREFIX', name: 'Mail Object Prefix', description: '', type: 'string', value: '[Lab]', default: '[LabsManager]', choices: [], can_change: true })
    if (url === '/api/v1/settings/admin/users/') return jsonResponse({ results: [{ id: 2, username: 'reader', name: 'Reader', last_login: null, is_active: true, is_staff: false, employee: null }] })
    if (url === '/api/v1/settings/admin/users/employee-options/') return jsonResponse({ results: [{ id: 8, name: 'Ada Test' }] })
    if (url === '/api/v1/settings/admin/users/2/employee/' && init?.method === 'PATCH') return jsonResponse({ id: 2, username: 'reader', name: 'Reader', last_login: null, is_active: true, is_staff: false, employee: { id: 8, name: 'Ada Test' } })
    if (url === '/api/v1/settings/admin/invitations/' && init?.method === 'GET') return jsonResponse({ results: invitationRows, can_assign_groups: canAssignGroups, group_options: canAssignGroups ? [{ id: 4, name: 'Readers' }] : [] })
    if (url === '/api/v1/settings/admin/invitations/' && init?.method === 'POST') {
      if (invitationError) return jsonResponse({ email: ['This e-mail address has already been invited.'] }, 400)
      const payload = JSON.parse(String(init.body)) as { employee_id: number | null; group_ids: number[] }
      const row = { id: 3, email: 'new@example.test', created: '2026-10-03T10:00:00Z', sent: '2026-10-03T10:00:01Z', accepted: false, key_expired: false, inviter: { id: 7, username: 'ada' }, employee: payload.employee_id ? { id: payload.employee_id, name: 'Ada Test' } : null, group_ids: payload.group_ids }
      invitationRows = [row, ...invitationRows]
      return jsonResponse(row, 201)
    }
    if (url === '/api/v1/settings/admin/invitations/1/' && init?.method === 'PATCH') {
      const payload = JSON.parse(String(init.body)) as { employee_id: number | null; group_ids?: number[] }
      invitationRows = invitationRows.map((row) => row.id === 1 ? { ...row, employee: payload.employee_id ? { id: payload.employee_id, name: 'Ada Test' } : null, group_ids: payload.group_ids ?? [] } : row)
      return jsonResponse(invitationRows[0])
    }
    if (url === '/api/v1/settings/admin/invitations/remove-expired/' && init?.method === 'POST') { invitationRows = invitationRows.filter((row) => !row.key_expired); return jsonResponse({ deleted: 1 }) }
    if (url === '/api/v1/settings/admin/notifications/') return jsonResponse({ results: [] })
    if (url === '/api/v1/settings/admin/notifications/check/') return jsonResponse({ counts: { stale: 1, overdue: 0, overload: 0 }, results: [] })
    if (url === '/api/v1/settings/admin/notifications/send/') return jsonResponse({ sent: 1, results: [] })
    if (url === '/api/v1/settings/admin/plugins/settings/') return jsonResponse({ settings: [] })
    if (url === '/api/v1/settings/admin/plugins/') return jsonResponse({ results: plugins, errors: [] })
    if (url === '/api/plugin/sample/activate/' || url === '/api/plugin/sifacexpenseimport/activate/') {
      if (pluginHold) await pluginHold
      if (pluginError) return jsonResponse({ detail: 'Activation failed' }, 400)
      const active = (JSON.parse(String(init?.body)) as { active: boolean }).active
      plugins = plugins.map((row) => row.key === url.split('/')[3] ? { ...row, active } : row)
      return jsonResponse({ active })
    }
    if (url === '/api/v1/settings/admin/plugins/reload/') return jsonResponse({ results: [], errors: [] })
    if (url === '/api/v1/settings/admin/plugins/sample/') return jsonResponse({ key: 'sample', human_name: 'Sample', description: 'Sample plugin', author: 'Ada', pub_date: null, version: '1', website: null, license: null, mixins: ['settings', 'schedule', 'urls'], sections: { settings: [], schedule: [], urls: { base_url: '/plugin/sample/', routes: [] } } })
    if (url === '/api/v1/settings/admin/plugins/broken/dependencies/install/' && init?.method === 'POST') { dependencyState = 'queued'; return jsonResponse(dependencies(), 202) }
    if (url === '/api/v1/settings/admin/plugins/broken/') return jsonResponse({ key: 'broken', human_name: 'Broken plugin', description: '', author: '', pub_date: null, version: null, website: null, license: null, mixins: [], active: false, is_builtin: false, error: true, sections: {}, dependencies: dependencies() })
    throw new Error(url)
  })
  render(<I18nProvider><BrowserRouter basename="/app"><AuthProvider><AppRouter /></AuthProvider></BrowserRouter></I18nProvider>)
  return calls
}

beforeEach(() => { vi.restoreAllMocks(); Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }) })

describe('Settings administration', () => {
  it('shows missing plugin requirements and starts a confirmed installation', async () => {
    const calls = renderAt('/app/settings/admin/plugins/broken')
    expect(await screen.findAllByText('Dépendances manquantes')).toHaveLength(2)
    expect(screen.getByText('icalendar')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Installer les dépendances' }))
    expect(screen.getByRole('alertdialog')).toHaveTextContent('icalendar ==7.3.0')
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Installer les dépendances' }))
    expect(await screen.findByText('Installation en attente')).toBeInTheDocument()
    expect(calls).toContain('POST /api/v1/settings/admin/plugins/broken/dependencies/install/')
  })
  it('shows the group only to staff and protects direct routes', async () => {
    renderAt('/app/settings/stale', false)
    expect(await screen.findByRole('heading', { name: 'Alertes d’échéance' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Général' })).not.toBeInTheDocument()
    cleanup()
    renderAt('/app/settings/admin/general', true)
    expect(await screen.findByRole('link', { name: 'Général' })).toHaveAttribute('href', '/app/settings/admin/general')
  })

  it('autosaves a general setting', async () => {
    const calls = renderAt('/app/settings/admin/general')
    const field = await screen.findByLabelText('Mail Object Prefix')
    fireEvent.change(field, { target: { value: '[Lab]' } })
    fireEvent.blur(field)
    expect(await screen.findByText('Enregistré')).toBeInTheDocument()
    expect(calls).toContain('PATCH /api/v1/settings/admin/general/settings/MAIL_OBJECT_PREFIX/')
  })

  it('lists users and opens the link sheet', async () => {
    const calls = renderAt('/app/settings/admin/users')
    expect(await screen.findByText('reader')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /actions.*reader/i }))
    await userEvent.click(await screen.findByText('Lier un employé'))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Employé lié'), '8')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(calls).toContain('PATCH /api/v1/settings/admin/users/2/employee/')
  })

  it('shows invitation columns and package status, sends then refreshes', async () => {
    const calls = renderAt('/app/settings/admin/users')
    const section = await screen.findByRole('region', { name: 'Invitations' })
    expect(await within(section).findByRole('columnheader', { name: 'E-mail' })).toBeInTheDocument()
    expect(within(section).getByRole('columnheader', { name: 'Date de création' })).toBeInTheDocument()
    expect(within(section).getByRole('columnheader', { name: 'Date d’envoi' })).toBeInTheDocument()
    expect(within(section).getByRole('columnheader', { name: 'Acceptée' })).toBeInTheDocument()
    expect(within(section).getByRole('columnheader', { name: 'Clé expirée' })).toBeInTheDocument()
    expect(within(section).getByRole('columnheader', { name: 'Invité par' })).toBeInTheDocument()
    expect(within(section).getByRole('row', { name: /expired@example.test/ })).toHaveTextContent('Oui')
    await userEvent.click(within(section).getByRole('button', { name: 'Inviter un utilisateur' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'E-mail' }), 'new@example.test')
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer l’invitation' }))
    expect(await within(section).findByText('new@example.test')).toBeInTheDocument()
    expect(calls).toContain('POST /api/v1/settings/admin/invitations/')
    expect(calls.filter((call) => call === 'GET /api/v1/settings/admin/invitations/').length).toBeGreaterThan(1)
  })

  it('prepares Employee and groups in the existing invitation sheet', async () => {
    renderAt('/app/settings/admin/users', true, false, true)
    const section = await screen.findByRole('region', { name: 'Invitations' })
    await userEvent.click(within(section).getByRole('button', { name: 'Inviter un utilisateur' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'E-mail' }), 'new@example.test')
    await userEvent.selectOptions(screen.getByLabelText('Employé lié'), '8')
    await userEvent.selectOptions(screen.getByLabelText('Groupes'), '4')
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer l’invitation' }))
    expect(await within(section).findByText('new@example.test')).toBeInTheDocument()
    const sent = vi.mocked(fetch).mock.calls.find(([url, init]) => String(url).endsWith('/admin/invitations/') && init?.method === 'POST')
    expect(JSON.parse(String(sent?.[1]?.body))).toEqual({ email: 'new@example.test', employee_id: 8, group_ids: [4] })
  })

  it('edits assignments on a pending invitation without resending it', async () => {
    const calls = renderAt('/app/settings/admin/users')
    const section = await screen.findByRole('region', { name: 'Invitations' })
    await userEvent.click(await within(section).findByRole('button', { name: /actions.*active@example.test/i }))
    await userEvent.click(await screen.findByText('Modifier la préparation'))
    await userEvent.selectOptions(screen.getByLabelText('Employé lié'), '8')
    await userEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await within(section).findByText('Ada Test')).toBeInTheDocument()
    expect(calls).toContain('PATCH /api/v1/settings/admin/invitations/1/')
    expect(calls).not.toContain('POST /api/v1/settings/admin/invitations/')
  })

  it('keeps the invitation sheet open on a business error', async () => {
    renderAt('/app/settings/admin/users', true, true)
    const section = await screen.findByRole('region', { name: 'Invitations' })
    await userEvent.click(within(section).getByRole('button', { name: 'Inviter un utilisateur' }))
    await userEvent.type(screen.getByRole('textbox', { name: 'E-mail' }), 'new@example.test')
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer l’invitation' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already been invited')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('confirms removal of expired invitations and refreshes the list', async () => {
    const calls = renderAt('/app/settings/admin/users')
    const section = await screen.findByRole('region', { name: 'Invitations' })
    await userEvent.click(within(section).getByRole('button', { name: 'Supprimer les expirées' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(calls).not.toContain('POST /api/v1/settings/admin/invitations/remove-expired/')
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Supprimer' }))
    expect(await within(section).findByText('1 invitation(s) supprimée(s).')).toBeInTheDocument()
    expect(within(section).queryByText('expired@example.test')).not.toBeInTheDocument()
    expect(within(section).getByText('active@example.test')).toBeInTheDocument()
  })

  it('runs both historical notification actions and renders plugins by mixin', async () => {
    const calls = renderAt('/app/settings/admin/notifications')
    await userEvent.click(await screen.findByRole('button', { name: 'Vérifier les notifications' }))
    expect(await screen.findByText('1 notification(s) ajoutée(s)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer les notifications en attente' }))
    expect(calls).toContain('POST /api/v1/settings/admin/notifications/send/')
    cleanup()
    renderAt('/app/settings/admin/plugins/sample')
    expect(await screen.findByRole('heading', { name: 'Sample' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tâches planifiées' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'URLs' })).toBeInTheDocument()
  })

  it('lists and reloads plugins', async () => {
    const calls = renderAt('/app/settings/admin/plugins')
    expect(await screen.findByRole('link', { name: 'Sample' })).toHaveAttribute('href', '/app/settings/admin/plugins/sample')
    expect(within(screen.getByRole('link', { name: 'Sample' }).closest('tr')!).getAllByText('Sample')).toHaveLength(2)
    expect(within(screen.getByRole('link', { name: 'Internal' }).closest('tr')!).getByText('Built-in')).toBeInTheDocument()
    expect(within(screen.getByRole('link', { name: 'SifacExpenseImport' }).closest('tr')!).queryByText(/^(Sample|Built-in)$/)).not.toBeInTheDocument()
    expect(screen.getByText('SifacExpenseImport')).toBeInTheDocument()
    expect(screen.getByText('Inactif')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Désactiver' })?.closest('tr')?.textContent).not.toContain('Internal')
    await userEvent.click(screen.getByRole('button', { name: 'Recharger les plugins' }))
    expect(calls).toContain('POST /api/v1/settings/admin/plugins/reload/')
  })

  it('activates and deactivates discovered plugins after confirmation', async () => {
    const calls = renderAt('/app/settings/admin/plugins')
    const row = (await screen.findByText('SifacExpenseImport')).closest('tr')!
    await userEvent.click(within(row).getByRole('button', { name: 'Activer' }))
    expect(within(row).getByText('Inactif')).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Activer' }))
    expect(await within(row).findByText('Actif')).toBeInTheDocument()
    expect(screen.getByText('Plugin activé.')).toBeInTheDocument()
    await userEvent.click(within(row).getByRole('button', { name: 'Désactiver' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Désactiver' }))
    expect(await within(row).findByText('Inactif')).toBeInTheDocument()
    expect(screen.getByText('Plugin désactivé.')).toBeInTheDocument()
    expect(calls.filter((call) => call.includes('/api/plugin/sifacexpenseimport/activate/'))).toHaveLength(2)
    expect(calls.filter((call) => call.includes('/plugins/reload/'))).toHaveLength(0)
  })

  it('keeps the plugin state and confirmation open when activation fails', async () => {
    renderAt('/app/settings/admin/plugins', true, false, false, true)
    const row = (await screen.findByText('SifacExpenseImport')).closest('tr')!
    await userEvent.click(within(row).getByRole('button', { name: 'Activer' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Activer' }))
    expect(await screen.findByText('Activation failed')).toBeInTheDocument()
    expect(within(row).getByText('Inactif')).toBeInTheDocument()
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
  })

  it('disables actions while a plugin change is pending', async () => {
    let release!: () => void
    const hold = new Promise<void>((resolve) => { release = resolve })
    renderAt('/app/settings/admin/plugins', true, false, false, false, hold)
    const row = (await screen.findByText('SifacExpenseImport')).closest('tr')!
    const reload = screen.getByRole('button', { name: 'Recharger les plugins' })
    await userEvent.click(within(row).getByRole('button', { name: 'Activer' }))
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Activer' }))
    expect(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Enregistrement…' })).toBeDisabled()
    expect(reload).toBeDisabled()
    release()
    expect(await within(row).findByText('Actif')).toBeInTheDocument()
  })
})
