import { Plus } from 'lucide-react'
import { useCallback, useRef, useState, type FormEvent } from 'react'
import { useOutletContext, useParams } from 'react-router-dom'
import { createMutableItem, deleteMutableItem, getMutableList, updateMutableItem, type MutableField, type MutableGroup, type MutableRow } from '../api/mutableLists'
import { normalizeMutationError } from '../api/errors'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { Input } from '../components/ui/input'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './SettingsHubPage.module.css'

type FormValue = string | number | boolean | null

function errorText(error: unknown, fallback: string) {
  const parsed = normalizeMutationError(error)
  return [...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ') || fallback
}

function display(field: MutableField, value: FormValue) {
  if (value === null || value === '') return '—'
  if (field.type === 'boolean') return value ? '✓' : '—'
  if (field.type === 'color') return <span className={styles.colorValue}><span className={styles.colorSwatch} style={{ backgroundColor: String(value) }} />{String(value)}</span>
  if (field.type === 'choice' || field.type === 'relation') return field.choices.find((choice) => String(choice.value) === String(value))?.label ?? String(value)
  return String(value)
}

function TreeCell({ value, level }: { value: FormValue; level: number }) {
  const depth = Math.min(Math.max(level, 0), 8)
  return <span className={styles.treeLabel} style={{ paddingInlineStart: `${depth * 0.85}rem` }}>
    {level > 0 && <span className={styles.treeBranch} aria-hidden="true">└─</span>}
    {value === null || value === '' ? '—' : String(value)}
  </span>
}

export function MutableListGroupPage() {
  const { groupKey } = useParams()
  const groups = useOutletContext<MutableGroup[] | null>()
  const group = groups?.find((entry) => entry.key === groupKey)
  const { t } = useTranslation()
  if (!groups) return <p role="status">{t('common.loading')}</p>
  if (!group) return <p>{t('mutableLists.unavailable')}</p>
  return <div className={styles.content}><h2 className="text-lg font-semibold">{group.label}</h2>
    {group.lists.map((item) => <MutableListSection key={item.key} listKey={item.key} />)}
  </div>
}

function MutableListSection({ listKey }: { listKey: string }) {
  const { t } = useTranslation()
  const loader = useCallback((key: string, signal: AbortSignal) => getMutableList(key, signal), [])
  const resource = useEmployeeResource(listKey, loader)
  const [editing, setEditing] = useState<MutableRow | 'create' | null>(null)
  const [deleting, setDeleting] = useState<MutableRow | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const focus = useRef<HTMLElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const data = resource.data

  async function remove() {
    if (!deleting || pending) return
    setPending(true); setError('')
    try {
      await deleteMutableItem(listKey, deleting.id)
      focus.current = section.current
      setDeleting(null)
      await resource.refresh()
    } catch (cause) { setError(errorText(cause, t('mutableLists.deleteError'))) }
    finally { setPending(false) }
  }

  return <section ref={section} tabIndex={-1} aria-label={data?.list.label} className={styles.section}>
    {data && <div className={styles.heading}><h3>{data.list.label}</h3>
      {data.list.capabilities.can_add && <Button size="sm" onClick={(event) => { focus.current = event.currentTarget; setEditing('create') }}><Plus aria-hidden="true" />{t('mutableLists.add')}</Button>}
    </div>}
    {resource.loading && <p role="status">{t('common.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('mutableLists.loadError')} <Button variant="ghost" onClick={resource.retry}>{t('common.retry')}</Button></Alert>}
    {data && <div className={styles.tableScroll}><table className={styles.table}><thead><tr>
      {data.list.columns.map((column) => <th key={column} scope="col">{data.list.fields.find((field) => field.key === column)?.label ?? column}</th>)}<th scope="col"><span className="sr-only">{t('mutableLists.actions')}</span></th>
    </tr></thead><tbody>{data.rows.map((row) => <tr key={row.id}>
      {data.list.columns.map((column) => <td key={column}>{data.list.renderers?.[column] === 'tree'
        ? <TreeCell value={row.values[column]} level={row.tree_level ?? 0} />
        : display(data.list.fields.find((field) => field.key === column)!, row.values[column])}</td>)}
      <td><ItemActionMenu label={t('common.actionsFor', { name: String(row.values.name ?? row.id) })} canChange={row.capabilities.can_change} canDelete={row.capabilities.can_delete} onOpen={() => {}} onTrigger={(trigger) => { focus.current = trigger }} onEdit={() => { setError(''); setEditing(row) }} onDelete={() => { setError(''); setDeleting(row) }} /></td>
    </tr>)}</tbody></table>{data.rows.length === 0 && <p className={styles.empty}>{t('mutableLists.empty')}</p>}</div>}
    {editing && data && <MutableItemSheet key={`${listKey}:${editing === 'create' ? 'create' : editing.id}`} listKey={listKey} fields={data.list.fields} row={editing === 'create' ? null : editing} onClose={() => setEditing(null)} onSaved={async () => { setEditing(null); await resource.refresh() }} focus={focus} />}
    {deleting && <ConfirmDialog title={t('mutableLists.deleteTitle')} description={t('mutableLists.deleteDescription', { name: String(deleting.values.name ?? deleting.id) })} pending={pending} error={error && <Alert tone="danger">{error}</Alert>} onCancel={() => { setDeleting(null); setError('') }} onConfirm={() => void remove()} returnFocus={focus} />}
  </section>
}

function MutableItemSheet({ listKey, fields, row, onClose, onSaved, focus }: {
  listKey: string; fields: MutableField[]; row: MutableRow | null
  onClose: () => void; onSaved: () => Promise<void>; focus: React.RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [values, setValues] = useState<Record<string, FormValue>>(() => Object.fromEntries(fields.map((field) => [field.key, row?.values[field.key] ?? field.default ?? (field.type === 'boolean' ? false : field.type === 'color' ? '#000000' : '')])))
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({})
  const editable = fields.filter((field) => !row || row.editable_fields.includes(field.key))

  async function save(event: FormEvent) {
    event.preventDefault()
    setPending(true); setError(''); setFieldErrors({})
    try {
      const payload = Object.fromEntries(editable.map((field) => [field.key, values[field.key]]))
      if (row) await updateMutableItem(listKey, row.id, payload)
      else await createMutableItem(listKey, payload)
      await onSaved()
    } catch (cause) {
      const parsed = normalizeMutationError(cause)
      setFieldErrors(parsed.fields)
      setError(parsed.messages.join(' ') || (!Object.keys(parsed.fields).length ? t('settings.saveError') : ''))
    } finally { setPending(false) }
  }

  return <Sheet open onOpenChange={(open) => { if (!open && !pending) onClose() }}><SheetContent finalFocus={focus}>
    <SheetHeader><SheetTitle>{t(row ? 'mutableLists.edit' : 'mutableLists.add')}</SheetTitle><SheetDescription>{t('mutableLists.formDescription')}</SheetDescription></SheetHeader>
    <form className={styles.form} onSubmit={(event) => void save(event)}>
      {fields.map((field) => {
        if (row && !row.editable_fields.includes(field.key)) return <div key={field.key}><span className="font-medium">{field.label}</span><p>{display(field, values[field.key])}</p></div>
        const value = values[field.key]
        return <label key={field.key}>{field.label}
          {field.type === 'boolean' ? <input type="checkbox" checked={value === true} onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.checked }))} />
            : field.type === 'choice' || field.type === 'relation' ? <select required={field.required} value={value === null ? '' : String(value)} className={styles.select} onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}><option value="">—</option>{field.choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</select>
              : <Input type={field.type === 'color' ? 'color' : 'text'} required={field.required} value={value === null ? '' : String(value)} onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))} />}
          {fieldErrors[field.key]?.map((message, index) => <span role="alert" className={styles.error} key={index}>{message}</span>)}
        </label>
      })}
      {error && <Alert tone="danger">{error}</Alert>}
      <div className={styles.sheetActions}><Button type="button" variant="ghost" onClick={onClose} disabled={pending}>{t('common.cancel')}</Button><Button type="submit" disabled={pending}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
