import { render, screen } from '@testing-library/react'
import { Menu } from 'lucide-react'
import { describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { Alert } from './Alert'
import { IconButton } from './IconButton'
import { StatusBadge } from './StatusBadge'

describe('UI primitives', () => {
  it('gives compact icon actions an accessible name', async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()
    render(<IconButton label="Ouvrir le menu" onClick={onClick}><Menu aria-hidden="true" /></IconButton>)

    await user.click(screen.getByRole('button', { name: 'Ouvrir le menu' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('keeps status and alert meaning available as text', () => {
    render(<><StatusBadge tone="success">Actif</StatusBadge><Alert tone="danger">Action impossible</Alert></>)
    expect(screen.getByText('Actif')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Action impossible')
  })
})
