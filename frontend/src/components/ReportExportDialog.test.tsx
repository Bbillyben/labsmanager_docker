import { createRef, useState } from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { ReportExportDialog } from './ReportExportDialog'

const api = vi.hoisted(() => ({ getReportTemplates: vi.fn(), exportReport: vi.fn() }))
vi.mock('../api/reports', () => api)

function mount(entity: 'project' | 'employee' = 'project', format: 'word' | 'pdf' = 'word', onClose = vi.fn()) {
  const trigger = createRef<HTMLButtonElement>()
  function Harness() {
    const [open, setOpen] = useState(true)
    return <I18nProvider><button ref={trigger}>Trigger</button>{open && <ReportExportDialog entity={entity} id={12} format={format} title="Exporter" timeframe={entity === 'employee'} returnFocus={trigger} onClose={() => { onClose(); setOpen(false) }} />}</I18nProvider>
  }
  const result = render(<Harness />)
  return { ...result, onClose, trigger }
}

describe('ReportExportDialog', () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['fr-FR'] })
    api.getReportTemplates.mockResolvedValue({ templates: [{ id: 3, name: 'Modèle A' }, { id: 4, name: 'Modèle B' }] })
    api.exportReport.mockResolvedValue({ blob: new Blob(['file']), filename: 'export.docx' })
    URL.createObjectURL = vi.fn(() => 'blob:report')
    URL.revokeObjectURL = vi.fn()
  })
  afterEach(() => { vi.clearAllMocks(); vi.restoreAllMocks() })

  it('selects the first backend template, downloads Word and closes', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const { onClose, trigger } = mount()
    const dialog = screen.getByRole('dialog')
    expect(await within(dialog).findByRole('option', { name: 'Modèle A' })).toBeInTheDocument()
    expect(within(dialog).getByRole('combobox', { name: 'Modèle' })).toHaveValue('3')
    expect(within(dialog).queryByLabelText('Du')).not.toBeInTheDocument()
    await userEvent.setup().click(within(dialog).getByRole('button', { name: 'Exporter' }))
    await waitFor(() => expect(api.exportReport).toHaveBeenCalledWith('project', 12, 'word', { template_id: 3 }))
    expect(click).toHaveBeenCalledOnce()
    expect(onClose).toHaveBeenCalledOnce()
    await waitFor(() => expect(trigger.current).toHaveFocus())
  })

  it('shows optional Employee dates, rejects inversion and submits PDF', async () => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mount('employee', 'pdf')
    const user = userEvent.setup()
    const dialog = screen.getByRole('dialog')
    await within(dialog).findByRole('option', { name: 'Modèle A' })
    const start = within(dialog).getByLabelText('Du') as HTMLInputElement
    const end = within(dialog).getByLabelText('Au') as HTMLInputElement
    expect(start.value).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(end.value).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    await user.clear(start)
    await user.type(start, '2026-12-31')
    await user.clear(end)
    await user.type(end, '2026-01-01')
    await user.click(within(dialog).getByRole('button', { name: 'Exporter' }))
    expect(await within(dialog).findByText('La date de début doit précéder la date de fin.')).toBeInTheDocument()
    expect(api.exportReport).not.toHaveBeenCalled()
    await user.clear(end)
    await user.click(within(dialog).getByRole('button', { name: 'Exporter' }))
    await waitFor(() => expect(api.exportReport).toHaveBeenCalledWith('employee', 12, 'pdf', { template_id: 3, start_date: '2026-12-31', end_date: null }))
  })

  it('disables export without templates and preserves an API error', async () => {
    api.getReportTemplates.mockResolvedValueOnce({ templates: [] })
    const { rerender, trigger } = mount()
    expect(await screen.findByText('Aucun modèle disponible')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exporter' })).toBeDisabled()
    rerender(<I18nProvider><button ref={trigger}>Trigger</button><ReportExportDialog entity="project" id={13} format="pdf" title="Exporter" timeframe={false} returnFocus={trigger} onClose={vi.fn()} /></I18nProvider>)
    api.exportReport.mockRejectedValueOnce(new Error('failed'))
    await screen.findByRole('option', { name: 'Modèle A' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Exporter' }))
    expect(await screen.findByText('Impossible de générer le rapport.')).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('keeps the dialog open and blocks another submission while generation is pending', async () => {
    let finish!: (value: { blob: Blob; filename: string }) => void
    api.exportReport.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const { onClose } = mount()
    await screen.findByRole('option', { name: 'Modèle A' })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Exporter' }))
    expect(screen.getByRole('button', { name: 'Export en cours…' })).toBeDisabled()
    expect(onClose).not.toHaveBeenCalled()
    finish({ blob: new Blob(['file']), filename: 'report.docx' })
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce())
    expect(api.exportReport).toHaveBeenCalledOnce()
  })

  it('renders the export form in English', async () => {
    Object.defineProperty(window.navigator, 'languages', { configurable: true, value: ['en-US'] })
    mount('employee', 'word')
    expect(await screen.findByRole('combobox', { name: 'Template' })).toBeInTheDocument()
    expect(screen.getByLabelText('From')).toBeInTheDocument()
    expect(screen.getByLabelText('To')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Export' })).toBeInTheDocument()
  })
})
