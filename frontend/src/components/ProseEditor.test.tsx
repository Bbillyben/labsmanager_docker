import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { ProseEditor } from './ProseEditor'

afterEach(() => { delete window.DjangoProseEditor })

it('uses the existing WYSIWYG and captures edits before its delayed textarea sync', async () => {
  Object.defineProperty(navigator, 'languages', { configurable: true, value: ['fr'] })
  const onChange = vi.fn()
  const destroy = vi.fn()
  const extension = { configure: () => ({}) }
  window.DjangoProseEditor = {
    Document: extension, Dropcursor: extension, Gapcursor: extension, Paragraph: extension,
    HardBreak: extension, Text: extension, Bold: extension, Italic: extension,
    Subscript: extension, Superscript: extension, Link: extension, Menu: extension,
    createEditor: (textarea) => {
      const wrapper = document.createElement('div')
      wrapper.className = 'prose-editor'
      const editable = document.createElement('div')
      editable.className = 'ProseMirror'
      editable.innerHTML = textarea.value
      textarea.before(wrapper)
      wrapper.append(textarea, editable)
      return destroy
    },
  }
  const view = render(<I18nProvider><ProseEditor initialHtml="<p>Before</p>" onChange={onChange} /></I18nProvider>)
  const editable = await waitFor(() => { const element = document.querySelector('.ProseMirror'); expect(element).not.toBeNull(); return element as HTMLElement })
  expect(screen.getByLabelText('Contenu de la note')).toHaveValue('<p>Before</p>')
  act(() => { editable.innerHTML = '<p>Immediately changed</p>' })
  await waitFor(() => expect(onChange).toHaveBeenCalledWith('<p>Immediately changed</p>'))
  view.unmount()
  expect(destroy).toHaveBeenCalledTimes(1)
})
