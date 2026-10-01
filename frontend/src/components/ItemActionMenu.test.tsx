import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { ItemActionMenu } from './ItemActionMenu'

beforeEach(() => Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] }))

function setup(canChange: boolean, canDelete: boolean, overrides: Partial<Parameters<typeof ItemActionMenu>[0]> = {}) {
  const onOpen = vi.fn()
  const onEdit = vi.fn()
  const onDelete = vi.fn()
  const onTrigger = vi.fn()
  render(<I18nProvider><ItemActionMenu label="Actions pour Badge" canChange={canChange} canDelete={canDelete}
    onOpen={onOpen} onEdit={onEdit} onDelete={onDelete} onTrigger={onTrigger} {...overrides} /></I18nProvider>)
  return { onOpen, onEdit, onDelete, onTrigger }
}

describe('ItemActionMenu', () => {
  it('renders no trigger or empty menu without actions', () => {
    setup(false, false)
    expect(screen.queryByRole('button', { name: 'Actions pour Badge' })).not.toBeInTheDocument()
  })

  it('shows an authorized Admin link even without business actions', async () => {
    setup(false, false, { adminUrl: '/admin/fund/budget/12/change/' })
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Badge' }))
    const link = await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })
    expect(link).toHaveAttribute('href', '/admin/fund/budget/12/change/')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
  })

  it('keeps Edit/Delete and separates the Admin link', async () => {
    const callbacks = setup(true, true, { adminUrl: '/admin/staff/employee/73/change/' })
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Badge' }))
    await screen.findByRole('menuitem', { name: 'Ouvrir dans l’administration' })
    expect(screen.getAllByRole('menuitem')).toHaveLength(3)
    expect(screen.getByRole('separator')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Modifier' }))
    expect(callbacks.onEdit).toHaveBeenCalledOnce()
  })

  it.each([
    [true, false, 'Modifier'],
    [false, true, 'Supprimer'],
  ])('shows only the allowed action for canChange=%s, canDelete=%s', async (canChange, canDelete, action) => {
    setup(canChange, canDelete)
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Badge' }))
    expect(await screen.findByRole('menuitem', { name: action })).toBeInTheDocument()
    expect(screen.getAllByRole('menuitem')).toHaveLength(1)
  })

  it('opens with keyboard, exposes the trigger, and restores focus on close', async () => {
    const { onOpen, onTrigger } = setup(true, true)
    const trigger = screen.getByRole('button', { name: 'Actions pour Badge' })
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(onTrigger).toHaveBeenCalledWith(trigger)
    expect(screen.getAllByRole('menuitem')).toHaveLength(2)
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it.each([
    ['Modifier', 'onEdit'],
    ['Supprimer', 'onDelete'],
  ] as const)('dispatches %s to the injected callback', async (action, callback) => {
    const callbacks = setup(true, true)
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Badge' }))
    await userEvent.click(await screen.findByRole('menuitem', { name: action }))
    expect(callbacks[callback]).toHaveBeenCalledTimes(1)
  })

  it('passes a generic finalFocus override to the menu primitive', async () => {
    const finalFocus = vi.fn(() => false)
    setup(true, false, { finalFocus })
    await userEvent.click(screen.getByRole('button', { name: 'Actions pour Badge' }))
    await screen.findByRole('menuitem', { name: 'Modifier' })
    await userEvent.keyboard('{Escape}')
    await waitFor(() => expect(finalFocus).toHaveBeenCalled())
  })
})
