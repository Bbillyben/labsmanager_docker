import { Download, Upload } from 'lucide-react'
import { useEffect, useState } from 'react'
import { commitImport, downloadImportErrors, getImportProfiles, getImportTemplate, previewImport, uploadImport, type ImportProfile, type ImportResult, type ImportRow, type ImportUpload } from '../api/imports'
import { normalizeMutationError } from '../api/errors'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'

const states = ['all', 'new', 'update', 'unchanged', 'error'] as const
type Filter = typeof states[number]

function saveFile(file: { blob: Blob; filename: string | null }, fallback: string) {
  const url = URL.createObjectURL(file.blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = file.filename ?? fallback
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function ImportRowsTable({ result, columns }: { result: ImportResult; columns: ImportProfile['preview_columns'] }) {
  const { t } = useTranslation()
  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(0)
  const rows = filter === 'all' ? result.rows : result.rows.filter((row) => row.state === filter)
  const size = 50
  const pages = Math.max(1, Math.ceil(rows.length / size))
  const current = Math.min(page, pages - 1)
  return <section className="grid gap-4">
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4" aria-label={t('import.summary')}>
      {(['new', 'update', 'unchanged', 'error'] as const).map((state) => <div className="rounded-md border border-border p-3" key={state}><span className="text-sm text-muted-foreground">{t(`import.state.${state}`)}</span><strong className="block text-lg">{result.summary[state]}</strong></div>)}
    </div>
    <div className="flex flex-wrap gap-2" role="group" aria-label={t('import.filter')}>
      {states.map((state) => <Button key={state} variant={filter === state ? 'primary' : 'secondary'} aria-pressed={filter === state} onClick={() => { setFilter(state); setPage(0) }}>{t(`import.state.${state}`)} ({state === 'all' ? result.rows.length : result.summary[state]})</Button>)}
    </div>
    <div className="overflow-x-auto rounded-md border border-border"><table className="w-full text-left text-sm"><thead className="bg-muted"><tr><th className="p-2">{t('import.status')}</th><th className="p-2">{t('import.row')}</th><th className="p-2">{t('import.identity')}</th>{columns.map((column) => <th key={column.key} className="min-w-24 whitespace-nowrap p-2">{column.label}</th>)}<th className="p-2">{t('import.detail')}</th></tr></thead><tbody>{rows.slice(current * size, (current + 1) * size).map((row: ImportRow) => <tr key={row.row_number} className="border-t border-border"><td className="p-2">{t(`import.state.${row.state}`)}</td><td className="p-2">{row.row_number}</td><td className="p-2">{row.identity || '—'}</td>{columns.map((column) => <td key={column.key} className="min-w-24 p-2">{row.values?.[column.key] || '—'}</td>)}<td className="p-2">{row.error_message ? <span className="text-destructive">{row.error_message}</span> : row.state === 'update' ? row.diff.map((item) => <div key={item.field}><strong>{item.field}:</strong> {t('import.old')} {item.old || '—'} → {t('import.new')} {item.new || '—'}</div>) : row.summary || '—'}</td></tr>)}</tbody></table></div>
    {pages > 1 && <div className="flex items-center justify-end gap-2"><Button disabled={current === 0} onClick={() => setPage(current - 1)}>{t('common.previous')}</Button><span>{current + 1} / {pages}</span><Button disabled={current + 1 === pages} onClick={() => setPage(current + 1)}>{t('common.next')}</Button></div>}
  </section>
}

export function ImportPage() {
  const { t } = useTranslation()
  const [profiles, setProfiles] = useState<ImportProfile[] | null>(null)
  const [profile, setProfile] = useState('')
  const [upload, setUpload] = useState<ImportUpload | null>(null)
  const [sheet, setSheet] = useState('')
  const [preview, setPreview] = useState<ImportResult | null>(null)
  const [final, setFinal] = useState<ImportResult | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const selected = profiles?.find((item) => item.key === profile)
  const structure = upload?.sheet_structures[sheet] ?? upload?.structure

  useEffect(() => { let mounted = true; getImportProfiles().then((data) => { if (mounted) setProfiles(data.items) }, (cause) => { if (mounted) setError(normalizeMutationError(cause).messages.join(' ') || t('import.loadError')) }); return () => { mounted = false } }, [t])

  async function run(action: () => Promise<void>) { if (pending) return; setPending(true); setError(''); try { await action() } catch (cause) { const normalized = normalizeMutationError(cause); setError([...normalized.messages, ...Object.values(normalized.fields).flat()].join(' ') || t('import.actionError')) } finally { setPending(false) } }
  function reset(nextProfile: string) { setProfile(nextProfile); setUpload(null); setSheet(''); setPreview(null); setFinal(null); setError('') }
  function changeSheet(value: string) { setSheet(value); setPreview(null); setFinal(null) }
  const phase = final ? 4 : preview ? 3 : upload ? 2 : profile ? 1 : 0

  return <main className="grid gap-6"><PageHeader title={t('navigation.import')} description={t('import.description')} />
    <ol className="flex flex-wrap gap-3 text-sm" aria-label={t('import.steps')}>{(['type', 'file', 'preview', 'confirm', 'result'] as const).map((step, index) => <li key={step} aria-current={phase === index ? 'step' : undefined} className={phase === index ? 'font-semibold' : 'text-muted-foreground'}>{index + 1}. {t(`import.step.${step}`)}</li>)}</ol>
    {error && <Alert tone="danger">{error}</Alert>}
    {!profiles && !error && <LoadingState message={t('common.loading')} />}
    {profiles && profiles.length === 0 && <p>{t('import.noProfiles')}</p>}
    {profiles && profiles.length > 0 && <section className="grid gap-3"><label className="grid gap-1 max-w-md">{t('import.type')}<select className="rounded-md border border-input bg-background p-2" value={profile} onChange={(event) => reset(event.target.value)}><option value="">{t('import.chooseType')}</option>{profiles.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>{selected && <p className="text-sm text-muted-foreground">{selected.description} · {selected.formats.join(', ').toUpperCase()}</p>}</section>}
    {selected && !final && <section className="grid gap-4"><div className="flex flex-wrap gap-2">{selected.template_formats.map((format) => <Button key={format} onClick={() => void run(async () => saveFile(await getImportTemplate(profile, format), `${profile}-template.${format}`))}><Download aria-hidden="true" />{t('import.template')} {format.toUpperCase()}</Button>)}</div>
      <label className="grid max-w-md gap-2 rounded-md border border-border p-4">{t('import.file')}<input type="file" accept={selected.formats.map((format) => `.${format}`).join(',')} disabled={pending} onChange={(event) => { const file = event.target.files?.[0]; setUpload(null); setPreview(null); setFinal(null); if (file) void run(async () => { const data = await uploadImport(profile, file); setUpload(data); setSheet(data.sheets[0] ?? '') }) }} /></label></section>}
    {upload && !final && <section className="grid gap-3"><h2 className="text-lg font-semibold">{t('import.fileInfo')}</h2><p>{upload.filename} · {(upload.size / 1024).toFixed(1)} KB · {upload.format.toUpperCase()}</p>{upload.sheets.length > 1 && <label className="grid max-w-md gap-1">{t('import.sheet')}<select className="rounded-md border border-input bg-background p-2" value={sheet} onChange={(event) => changeSheet(event.target.value)}>{upload.sheets.map((name) => <option key={name} value={name}>{name}</option>)}</select></label>}
      <p>{t('import.rows')}: {structure?.rows} · {t('import.columns')}: {structure?.columns}</p>
      <p>{t('import.recognized')}: {structure?.recognized.join(', ') || '—'}</p><p>{t('import.missing')}: {structure?.missing.join(', ') || '—'}</p><p>{t('import.extra')}: {structure?.extra.join(', ') || '—'}</p>
      {!preview && <Button disabled={pending} onClick={() => void run(async () => { const result = await previewImport(profile, upload.import_token, sheet); setPreview(result) })}><Upload aria-hidden="true" />{t('import.check')}</Button>}</section>}
    {preview && !final && <section className="grid gap-5"><h2 className="text-lg font-semibold">{t('import.preview')}</h2>{preview.global_errors.map((message, index) => <Alert key={index} tone="danger">{message}</Alert>)}<ImportRowsTable result={preview} columns={selected?.preview_columns ?? []} />{preview.summary.error > 0 && <p className="text-sm text-muted-foreground">{t(preview.can_commit ? 'import.partialHint' : 'import.blocked')}</p>}
      <div className="flex flex-wrap gap-2">{preview.summary.error > 0 && preview.import_token && <Button disabled={pending} onClick={() => void run(async () => saveFile(await downloadImportErrors(profile, preview.import_token!), `${profile}-errors.csv`))}><Download aria-hidden="true" />{t('import.errorsDownload')}</Button>}{preview.can_commit && preview.import_token && <Button variant="primary" disabled={pending} onClick={() => void run(async () => setFinal(await commitImport(profile, preview.import_token!)))}>{t('import.confirm')}</Button>}</div></section>}
    {final && <section className="grid gap-5"><h2 className="text-lg font-semibold">{t('import.complete')}</h2>{final.global_errors.map((message, index) => <Alert key={index} tone="danger">{message}</Alert>)}<ImportRowsTable result={final} columns={selected?.preview_columns ?? []} /><Button onClick={() => reset(profile)}>{t('import.again')}</Button></section>}
  </main>
}
