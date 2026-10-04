import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { PrintButton } from './PrintButton'
import { PrintProvider } from './PrintProvider'
import { getPrintRenderer, registerPrintRenderer, type PrintRendererProps } from './registry'

function TestRenderer({ state, onReady }: PrintRendererProps<{ value: string }>) {
  useEffect(() => { onReady() }, [onReady])
  return <p>{state.value}</p>
}

describe('print registry and shell', () => {
  it('accepts an external renderer, passes state and prints only after ready', async () => {
    const user = userEvent.setup()
    const print = vi.spyOn(window, 'print').mockImplementation(() => {})
    if (!getPrintRenderer('test-renderer')) registerPrintRenderer({ key: 'test-renderer', label: 'Test', render: TestRenderer, defaultPage: { size: 'A4', orientation: 'portrait' } })
    expect(getPrintRenderer('unknown')).toBeNull()
    render(<I18nProvider><PrintProvider><div>Interactive view</div><PrintButton createRequest={() => ({ renderer: 'test-renderer', title: 'Test title', subtitle: 'Period', state: { value: 'Current data' } })} /></PrintProvider></I18nProvider>)
    const trigger = screen.getByRole('button', { name: 'Print' })
    await user.click(trigger)
    const dialog = await screen.findByRole('dialog', { name: 'Test title' })
    expect(screen.getByRole('button', { name: 'Back' })).toHaveFocus()
    expect(dialog).toHaveTextContent('Period')
    expect(dialog).toHaveTextContent('Current data')
    expect(screen.getByText('Interactive view').parentElement).toHaveAttribute('aria-hidden', 'true')
    await user.click(screen.getByRole('button', { name: 'Print' }))
    expect(print).toHaveBeenCalledOnce()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByText('Interactive view')).toBeInTheDocument()
    await waitFor(() => expect(trigger).toHaveFocus())
    print.mockRestore()
  })

  it('shows a controlled error for an unknown renderer', async () => {
    const user = userEvent.setup()
    render(<I18nProvider><PrintProvider><PrintButton createRequest={() => ({ renderer: 'unknown', title: 'Unknown', state: {} })} /></PrintProvider></I18nProvider>)
    await user.click(screen.getByRole('button', { name: 'Print' }))
    const dialog = await screen.findByRole('dialog', { name: 'Unknown' })
    expect(dialog).toHaveTextContent('This print format is unavailable.')
    expect(screen.getByRole('button', { name: 'Print' })).toBeDisabled()
  })
})
