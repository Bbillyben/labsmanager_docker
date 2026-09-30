import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EntityActionMenu } from './EntityActionMenu'

afterEach(() => vi.restoreAllMocks())

describe('EntityActionMenu', () => {
  it('renders nothing without available actions', () => {
    render(<EntityActionMenu label="Actions" groups={[[], []]} />)
    expect(screen.queryByRole('button', { name: 'Actions' })).not.toBeInTheDocument()
  })

  it('shows one action without a separator and executes it', async () => {
    const onSelect = vi.fn()
    render(<EntityActionMenu label="Actions" groups={[[], [{ id: 'word', label: 'Word', onSelect }]]} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Actions' }))
    const menu = await screen.findByRole('menu')
    expect(within(menu).queryByRole('separator')).not.toBeInTheDocument()
    await userEvent.setup().click(within(menu).getByRole('menuitem', { name: 'Word' }))
    expect(onSelect).toHaveBeenCalledOnce()
  })

  it('groups multiple actions, disables an action and supports keyboard focus', async () => {
    const user = userEvent.setup()
    const onTrigger = vi.fn()
    const onEdit = vi.fn()
    render(<EntityActionMenu label="Actions" onTrigger={onTrigger} groups={[
      [{ id: 'word', label: 'Word', disabled: true, onSelect: vi.fn() }, { id: 'pdf', label: 'PDF', onSelect: vi.fn() }],
      [{ id: 'edit', label: 'Edit', onSelect: onEdit }],
    ]} />)
    const trigger = screen.getByRole('button', { name: 'Actions' })
    trigger.focus()
    await user.keyboard('{Enter}')
    const menu = await screen.findByRole('menu')
    expect(within(menu).getAllByRole('separator')).toHaveLength(1)
    expect(within(menu).getByRole('menuitem', { name: 'Word' })).toHaveAttribute('aria-disabled', 'true')
    await user.click(within(menu).getByRole('menuitem', { name: 'Edit' }))
    expect(onTrigger).toHaveBeenCalledWith(trigger)
    expect(onEdit).toHaveBeenCalledOnce()
    expect(trigger).toHaveFocus()
  })
})
