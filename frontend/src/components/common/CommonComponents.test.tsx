import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import { CopyableValue } from './CopyableValue'
import { PersistentCollapsibleSection } from './PersistentCollapsibleSection'

const originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard')
const originalExecCommand = Object.getOwnPropertyDescriptor(document, 'execCommand')

function setClipboard(value: { writeText: (value: string) => Promise<void> } | undefined) {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value })
}

function setExecCommand(value: ((command: string) => boolean) | undefined) {
  Object.defineProperty(document, 'execCommand', { configurable: true, value })
}

function restoreProperty(target: object, property: string, descriptor: PropertyDescriptor | undefined) {
  if (descriptor) Object.defineProperty(target, property, descriptor)
  else Reflect.deleteProperty(target, property)
}

function renderTranslated(node: ReactNode) {
  return render(<I18nProvider>{node}</I18nProvider>)
}

describe('CopyableValue', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    setClipboard(undefined)
    setExecCommand(undefined)
  })

  afterEach(() => {
    restoreProperty(navigator, 'clipboard', originalClipboard)
    restoreProperty(document, 'execCommand', originalExecCommand)
  })

  it('uses the Clipboard API and confirms only after it resolves', async () => {
    let resolveCopy: (() => void) | undefined
    const writeText = vi.fn(() => new Promise<void>((resolve) => { resolveCopy = resolve }))
    setClipboard({ writeText })
    renderTranslated(<CopyableValue value="alpha" />)

    fireEvent.click(screen.getByRole('button', { name: 'Copier la valeur' }))
    expect(writeText).toHaveBeenCalledWith('alpha')
    expect(screen.queryByRole('button', { name: 'Copié' })).not.toBeInTheDocument()

    resolveCopy?.()
    expect(await screen.findByRole('button', { name: 'Copié' })).toBeInTheDocument()
  })

  it('falls back to a temporary selection when Clipboard API is unavailable on HTTP', async () => {
    let selectedValue = ''
    const execCommand = vi.fn(() => {
      selectedValue = (document.activeElement as HTMLTextAreaElement).value
      return true
    })
    setExecCommand(execCommand)
    renderTranslated(<CopyableValue value="LAN value"><strong>Visible value</strong></CopyableValue>)
    const button = screen.getByRole('button', { name: 'Copier la valeur' })
    button.focus()

    fireEvent.click(button)

    expect(await screen.findByRole('button', { name: 'Copié' })).toBeInTheDocument()
    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(selectedValue).toBe('LAN value')
    expect(document.activeElement).toBe(button)
    expect(document.querySelector('textarea[aria-hidden="true"]')).not.toBeInTheDocument()
  })

  it('falls back after Clipboard API rejection and gives no false success feedback', async () => {
    const writeText = vi.fn().mockRejectedValue(new DOMException('Blocked', 'NotAllowedError'))
    const execCommand = vi.fn().mockReturnValue(false)
    setClipboard({ writeText })
    setExecCommand(execCommand)
    renderTranslated(<CopyableValue value="alpha" />)

    fireEvent.click(screen.getByRole('button', { name: 'Copier la valeur' }))

    await waitFor(() => expect(execCommand).toHaveBeenCalledWith('copy'))
    expect(screen.queryByRole('button', { name: 'Copié' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copier la valeur' })).toBeInTheDocument()
  })
})

describe('PersistentCollapsibleSection', () => {
  beforeEach(() => localStorage.clear())

  it('uses the full title row as an accessible persistent trigger', async () => {
    const user = userEvent.setup()
    renderTranslated(<PersistentCollapsibleSection storageKey="section-open" title="Informations générales"><p>Contenu</p></PersistentCollapsibleSection>)
    const trigger = screen.getByRole('button', { name: 'Replier Informations générales' })

    expect(trigger).toHaveTextContent('Informations générales')
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    trigger.focus()
    await user.keyboard('{Enter}')

    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Contenu')).not.toBeInTheDocument()
    expect(localStorage.getItem('section-open')).toBe('false')
  })
})
