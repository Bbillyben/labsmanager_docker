import { createRef, useState } from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SettingData } from '../api/settings'
import { I18nProvider } from '../i18n/I18nProvider'
import { SettingsSheet } from './SettingsSheet'

const rows: SettingData[] = [
  { key: 'EXPENSE_CALCULATION', name: 'Mode de calcul des dépenses', description: 'Définit la source des dépenses.', type: 'choice', value: 's', default: 's', choices: [{ value: 's', label: 'Simple' }, { value: 'e', label: 'Dépenses individuelles' }, { value: 'h', label: 'Hybride' }] },
  { key: 'LEADER_EDIT_FUND', name: 'Le responsable peut modifier les financements', description: 'Autorise le responsable du projet.', type: 'boolean', value: true, default: true, choices: [] },
  { key: 'EMPLOYEE_EDIT_MILESTONE', name: 'Les employés peuvent modifier leurs jalons', description: 'Autorise les employés.', type: 'boolean', value: false, default: true, choices: [] },
]

function mount(load = vi.fn().mockResolvedValue({ settings: rows }), save = vi.fn().mockImplementation(async (key, value) => ({ ...rows.find((row) => row.key === key)!, value }))) {
  const trigger = createRef<HTMLButtonElement>()
  const onClose = vi.fn()
  function Harness() {
    const [open, setOpen] = useState(true)
    return <I18nProvider><button ref={trigger}>Trigger</button>{open && <SettingsSheet title="Paramètres du projet" description="Sauvegarde immédiate" load={load} save={save} returnFocus={trigger} onClose={(changed) => { onClose(changed); setOpen(false) }} />}</I18nProvider>
  }
  render(<Harness />)
  return { load, save, onClose, trigger }
}

beforeEach(() => Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] }))
afterEach(() => vi.restoreAllMocks())

describe('SettingsSheet', () => {
  it('renders backend metadata and saves choices and booleans immediately', async () => {
    const { save, onClose, trigger } = mount()
    const user = userEvent.setup()
    const dialog = screen.getByRole('dialog')
    expect(screen.getByRole('status')).toHaveTextContent('Chargement')
    const choice = await within(dialog).findByRole('combobox', { name: 'Mode de calcul des dépenses' })
    expect(choice).toHaveValue('s')
    expect(within(dialog).getByText('Définit la source des dépenses.')).toBeInTheDocument()
    expect(within(dialog).getByRole('option', { name: 'Dépenses individuelles' })).toBeInTheDocument()
    const leader = within(dialog).getByRole('switch', { name: 'Le responsable peut modifier les financements' })
    const employee = within(dialog).getByRole('switch', { name: 'Les employés peuvent modifier leurs jalons' })
    expect(leader).toBeChecked()
    expect(employee).not.toBeChecked()
    await user.selectOptions(choice, 'e')
    await waitFor(() => expect(choice).toHaveValue('e'))
    await user.selectOptions(choice, 'h')
    await waitFor(() => expect(choice).toHaveValue('h'))
    await user.click(leader)
    await waitFor(() => expect(leader).not.toBeChecked())
    await user.click(leader)
    await waitFor(() => expect(leader).toBeChecked())
    expect(save.mock.calls).toEqual([
      ['EXPENSE_CALCULATION', 'e'], ['EXPENSE_CALCULATION', 'h'],
      ['LEADER_EDIT_FUND', false], ['LEADER_EDIT_FUND', true],
    ])
    await user.click(within(dialog).getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledWith(true)
    await waitFor(() => expect(trigger.current).toHaveFocus())
  })

  it('keeps server state after a failed mutation and shows its error', async () => {
    const save = vi.fn().mockRejectedValue(new Error('offline'))
    mount(undefined, save)
    const leader = await screen.findByRole('switch', { name: 'Le responsable peut modifier les financements' })
    await userEvent.setup().click(leader)
    expect(await screen.findByText('Impossible d’enregistrer ce paramètre.')).toBeInTheDocument()
    expect(leader).toBeChecked()
    expect(leader).not.toBeDisabled()
  })

  it('keeps the field pending and prevents closure during a mutation', async () => {
    let finish!: (setting: SettingData) => void
    const save = vi.fn().mockImplementation(() => new Promise<SettingData>((resolve) => { finish = resolve }))
    const { onClose } = mount(undefined, save)
    const choice = await screen.findByRole('combobox', { name: 'Mode de calcul des dépenses' })
    await userEvent.setup().selectOptions(choice, 'e')
    expect(await screen.findByText('Enregistrement…')).toBeInTheDocument()
    expect(choice).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Fermer' })).toBeDisabled()
    expect(onClose).not.toHaveBeenCalled()
    finish({ ...rows[0], value: 'e' })
    await waitFor(() => expect(choice).toHaveValue('e'))
  })

  it('retries a loading error and closes without a mutation', async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ settings: rows })
    const { onClose } = mount(load)
    expect(await screen.findByText('Impossible de charger les paramètres.')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(await screen.findByRole('combobox', { name: 'Mode de calcul des dépenses' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Fermer' }))
    expect(onClose).toHaveBeenCalledWith(false)
  })
})
