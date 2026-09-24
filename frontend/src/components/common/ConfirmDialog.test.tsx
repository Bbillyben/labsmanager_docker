import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import { ConfirmDialog } from './ConfirmDialog'

beforeEach(() => Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] }))
it('opens an accessible confirmation and cancellation never confirms', async () => {
  const onConfirm = vi.fn(), onCancel = vi.fn()
  render(<I18nProvider><ConfirmDialog title="Confirmation" description="Définitif" pending={false} onConfirm={onConfirm} onCancel={onCancel} returnFocus={createRef()} /></I18nProvider>)
  expect(screen.getByRole('alertdialog', { name: 'Confirmation' })).toHaveAccessibleDescription('Définitif')
  await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
  expect(onCancel).toHaveBeenCalledOnce()
  expect(onConfirm).not.toHaveBeenCalled()
})
it('blocks confirmation while the request is pending', async () => {
  const onConfirm = vi.fn()
  render(<I18nProvider><ConfirmDialog title="Confirmation" description="Définitif" pending onConfirm={onConfirm} onCancel={vi.fn()} returnFocus={createRef()} /></I18nProvider>)
  expect(screen.getByRole('button', { name: 'Enregistrement…' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Annuler' })).toBeDisabled()
})
