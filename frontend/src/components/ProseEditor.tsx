import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { useTranslation } from '../i18n/i18n'

type EditorExtension = { configure?: (options: object) => unknown }
type EditorLibrary = {
  [name: string]: unknown
  Link?: EditorExtension
  Menu?: EditorExtension
  createEditor: (textarea: HTMLTextAreaElement, extensions: unknown[]) => (() => void) | void
}

declare global { interface Window { DjangoProseEditor?: EditorLibrary } }

let editorScript: Promise<EditorLibrary> | null = null

function loadEditor(): Promise<EditorLibrary> {
  for (const file of ['editor.css', 'material-icons.css']) {
    if (!document.querySelector(`link[data-prose-editor="${file}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = `/static/django_prose_editor/${file}`
      link.dataset.proseEditor = file
      document.head.append(link)
    }
  }
  if (window.DjangoProseEditor) return Promise.resolve(window.DjangoProseEditor)
  if (!editorScript) editorScript = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = '/static/django_prose_editor/editor.js'
    script.onload = () => window.DjangoProseEditor ? resolve(window.DjangoProseEditor) : reject(new Error('Editor unavailable'))
    script.onerror = () => { editorScript = null; reject(new Error('Editor unavailable')) }
    document.head.append(script)
  })
  return editorScript
}

export function ProseEditor({ initialHtml, onChange }: { initialHtml: string; onChange: (html: string) => void }) {
  const { t } = useTranslation()
  const textarea = useRef<HTMLTextAreaElement>(null)
  const onChangeRef = useRef(onChange)
  const [error, setError] = useState(false)
  useEffect(() => { onChangeRef.current = onChange }, [onChange])

  useEffect(() => {
    let active = true
    let destroy: (() => void) | void
    let observer: MutationObserver | null = null
    const source = textarea.current
    if (!source) return
    const changed = () => onChangeRef.current(source.value)
    source.addEventListener('input', changed)
    void loadEditor().then((library) => {
      if (!active) return
      const names = ['Document', 'Dropcursor', 'Gapcursor', 'Paragraph', 'HardBreak', 'Text', 'Bold', 'Italic', 'Subscript', 'Superscript']
      const extensions: unknown[] = names.map((name) => library[name]).filter(Boolean)
      if (library.Link) extensions.push(library.Link.configure?.({ openOnClick: false }) ?? library.Link)
      if (library.Menu) extensions.push(library.Menu.configure?.({ config: {} }) ?? library.Menu)
      destroy = library.createEditor(source, extensions)
      const editable = source.parentElement?.querySelector('.ProseMirror')
      if (editable) {
        observer = new MutationObserver(() => onChangeRef.current(editable.innerHTML))
        observer.observe(editable, { childList: true, characterData: true, attributes: true, subtree: true })
      }
    }).catch(() => { if (active) setError(true) })
    return () => { active = false; source.removeEventListener('input', changed); observer?.disconnect(); destroy?.() }
  }, [])

  return <div style={{ '--body-bg': 'var(--background)', '--body-fg': 'var(--foreground)', '--border-color': 'var(--border)' } as CSSProperties}>
    {error && <p role="alert">{t('notes.editorError')}</p>}
    <textarea ref={textarea} defaultValue={initialHtml} aria-label={t('notes.content')} className="min-h-48 w-full rounded-md border border-input bg-background p-3" />
  </div>
}
