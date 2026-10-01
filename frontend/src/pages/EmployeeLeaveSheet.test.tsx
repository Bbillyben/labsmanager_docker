import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmployeeLeave } from '../api/employees'
import { ApiError } from '../api/errors'
import { EmployeeLeaveSheet } from './EmployeeLeaveSheet'

const api = vi.hoisted(() => ({ getLeaveTypes: vi.fn(), createEmployeeLeave: vi.fn(), updateEmployeeLeave: vi.fn(), deleteEmployeeLeave: vi.fn() }))
vi.mock('../api/employees', () => api)
const leave: EmployeeLeave = { id: 7, type: { id: 3, name: 'Congés payés', short_name: 'CP', color: '#336699' }, start_date: '2026-10-06', start_period: 'ST', end_date: '2026-10-06', end_period: 'EN', day_count: 1, comment: 'Famille' }
const capabilities = { can_add: true, can_change: true, can_delete: true }
const callbacks = { onClose: vi.fn(), onSaved: vi.fn(), onDeleted: vi.fn() }
beforeEach(() => {
  vi.clearAllMocks()
  api.getLeaveTypes.mockResolvedValue([{ id: 3, name: 'Congés payés', short_name: 'CP', color: '#336699', parent_id: null, depth: 0 }, { id: 4, name: 'RTT', short_name: 'RTT', color: '#223344', parent_id: 3, depth: 1 }])
  api.createEmployeeLeave.mockResolvedValue(leave)
  api.updateEmployeeLeave.mockResolvedValue(leave)
  api.deleteEmployeeLeave.mockResolvedValue(undefined)
})

describe('shared Employee Leave Sheet', () => {
  it('shows the backend Admin link for an existing Leave', async () => {
    render(<EmployeeLeaveSheet employeeId="12" leave={{ ...leave, admin_url: '/admin/leave/leave/7/change/' }} capabilities={{ can_add: false, can_change: false, can_delete: false }} {...callbacks} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Actions pour Congés payés' }))
    expect(await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })).toHaveAttribute('href', '/admin/leave/leave/7/change/')
  })
  it('is read-only without capabilities', async () => {
    render(<EmployeeLeaveSheet employeeId="12" leave={leave} capabilities={{ can_add: false, can_change: false, can_delete: false }} {...callbacks} />)
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Famille')).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Modifier l’absence' })).not.toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
  })

  it('edits and cancels without mutation, then saves', async () => {
    const user = userEvent.setup()
    render(<EmployeeLeaveSheet employeeId="12" leave={leave} capabilities={capabilities} {...callbacks} />)
    const edit = await screen.findByRole('button', { name: 'Modifier l’absence' })
    expect(edit.querySelector('svg.lucide-pencil')).toHaveAttribute('aria-hidden', 'true')
    expect(edit).toHaveClass('bg-secondary')
    expect(screen.getByRole('button', { name: 'Supprimer' }).querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    await user.click(edit)
    await screen.findByRole('option', { name: /RTT/ })
    await user.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(api.updateEmployeeLeave).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Modifier l’absence' }))
    await user.selectOptions(screen.getByLabelText('Type'), '4')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.updateEmployeeLeave).toHaveBeenCalledWith('12', 7, expect.objectContaining({ type_id: 4 })))
    expect(callbacks.onSaved).toHaveBeenCalledWith(leave)
  })

  it('creates with prefilled full-day dates and confirms deletion', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<EmployeeLeaveSheet employeeId="12" leave={null} initialDates={{ start_date: '2026-10-06', end_date: '2026-10-10' }} capabilities={capabilities} {...callbacks} />)
    await screen.findByRole('option', { name: /Congés payés/ })
    expect(screen.getByLabelText('Début')).toHaveValue('2026-10-06')
    expect(screen.getByLabelText('Fin')).toHaveValue('2026-10-10')
    expect(screen.getByLabelText('Début de l’absence')).toHaveValue('ST')
    expect(screen.getByLabelText('Fin de l’absence')).toHaveValue('EN')
    await user.selectOptions(screen.getByLabelText('Type'), '3')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    await waitFor(() => expect(api.createEmployeeLeave).toHaveBeenCalledWith('12', expect.objectContaining({ start_period: 'ST', end_period: 'EN', end_date: '2026-10-10' })))
    unmount()
    render(<EmployeeLeaveSheet employeeId="12" leave={leave} capabilities={capabilities} {...callbacks} />)
    await user.click(await screen.findByRole('button', { name: 'Supprimer' }))
    expect(api.deleteEmployeeLeave).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Supprimer' }))
    await waitFor(() => expect(api.deleteEmployeeLeave).toHaveBeenCalledWith('12', 7))
    expect(callbacks.onDeleted).toHaveBeenCalled()
  })

  it('keeps form values after an overlap error', async () => {
    const user = userEvent.setup()
    api.createEmployeeLeave.mockRejectedValue(new ApiError(400, { non_field_errors: ['Overlapping leave'] }))
    render(<EmployeeLeaveSheet employeeId="12" leave={null} initialDates={{ start_date: '2026-10-06', end_date: '2026-10-10' }} capabilities={capabilities} {...callbacks} />)
    await screen.findByRole('option', { name: /Congés payés/ })
    await user.selectOptions(screen.getByLabelText('Type'), '3')
    await user.type(screen.getByLabelText('Commentaire'), 'Planned')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByText('Overlapping leave')).toBeInTheDocument()
    expect(screen.getByLabelText('Commentaire')).toHaveValue('Planned')
    expect(screen.getByLabelText('Fin')).toHaveValue('2026-10-10')
    expect(callbacks.onSaved).not.toHaveBeenCalled()
  })

  it('prevents another submission while creation is pending', async () => {
    const user = userEvent.setup()
    let finish!: (value: EmployeeLeave) => void
    api.createEmployeeLeave.mockImplementation(() => new Promise<EmployeeLeave>((resolve) => { finish = resolve }))
    render(<EmployeeLeaveSheet employeeId="12" leave={null} initialDates={{ start_date: '2026-10-06', end_date: '2026-10-06' }} capabilities={capabilities} {...callbacks} />)
    await screen.findByRole('option', { name: /Congés payés/ })
    await user.selectOptions(screen.getByLabelText('Type'), '3')
    await user.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(screen.getByRole('button', { name: 'Enregistrer' })).toBeDisabled()
    expect(api.createEmployeeLeave).toHaveBeenCalledTimes(1)
    finish(leave)
    await waitFor(() => expect(callbacks.onSaved).toHaveBeenCalledTimes(1))
  })
})
