import { Plus } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { deleteOrganization, listOrganizations, type Organization, type OrganizationKind, type OrganizationList } from '../api/organizations'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { LoadingState } from '../components/LoadingState'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { OrganizationFormSheet } from './OrganizationSheets'
import styles from './EmployeeListPage.module.css'

export function OrganizationListPage({ kind }: { kind: OrganizationKind }) {
  const { t } = useTranslation()
  const [query, setQuery] = useSearchParams()
  const navigate = useNavigate()
  const search = query.get('search') ?? ''
  const ordering = ['short_name', '-short_name', 'name', '-name'].includes(query.get('ordering') ?? '') ? query.get('ordering')! : 'short_name'
  const offset = Math.max(0, Number(query.get('offset')) || 0)
  const limit = 25
  const [draft, setDraft] = useState(search)
  const [result, setResult] = useState<OrganizationList | null>(null)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)
  const [editing, setEditing] = useState<Organization | null | 'add'>(null)
  const [deleting, setDeleting] = useState<Organization | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const params = new URLSearchParams({ search, ordering, offset: String(offset), limit: String(limit) })
  const url = params.toString()
  useEffect(() => { setDraft(search) }, [search])
  useEffect(() => {
    const controller = new AbortController()
    listOrganizations(kind, url, controller.signal).then((data) => { if (!controller.signal.aborted) { setResult(data); setError(false) } }, () => { if (!controller.signal.aborted) setError(true) })
    return () => controller.abort()
  }, [kind, url, revision])
  function update(values: Record<string, string>) { const next = new URLSearchParams(query); for (const [key, value] of Object.entries(values)) { if (value) next.set(key, value); else next.delete(key) } setQuery(next) }
  function submit(event: FormEvent) { event.preventDefault(); update({ search: draft.trim(), offset: '' }) }
  async function remove() {
    if (!deleting) return
    const outcome = await mutation.run(() => deleteOrganization(kind, deleting.id))
    if (outcome) { setDeleting(null); setRevision((value) => value + 1) }
  }
  const title = t(kind === 'institutions' ? 'organization.institutions' : 'organization.funders')
  const mutationError = mutation.error ? normalizeMutationError(mutation.error) : null
  return <>
    <PageHeader title={title} />
    <div className="flex justify-end">{result?.capabilities.can_add && <Button onClick={(event) => { focus.current = event.currentTarget; setEditing('add') }}><Plus aria-hidden="true" />{t(kind === 'institutions' ? 'organization.addInstitution' : 'organization.addFunder')}</Button>}</div>
    <form className="flex flex-wrap gap-2" onSubmit={submit}><label className="sr-only" htmlFor="organization-search">{t('organization.search')}</label><input id="organization-search" className="h-9 min-w-64 rounded-md border border-input bg-background px-3" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={t('organization.search')} /><Button type="submit" variant="secondary">{t('common.search')}</Button></form>
    {error && <Alert tone="danger">{t('organization.loadError')} <Button onClick={() => setRevision((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {!error && !result && <LoadingState message={t('common.loading')} />}
    {result && !error && <section aria-label={title}><p className={styles.summary}>{t('organization.count', { count: result.count })}</p><div className={styles.scroll}><table className={styles.table}><thead><tr>
      <SortableTableHeader label={t('organization.shortName')} field="short_name" ordering={ordering} onSort={(next) => update({ ordering: next, offset: '' })} />
      <SortableTableHeader label={t('organization.name')} field="name" ordering={ordering} onSort={(next) => update({ ordering: next, offset: '' })} />
      <th scope="col">{t('organization.actions')}</th>
    </tr></thead><tbody>{result.results.map((org) => <tr key={org.id} tabIndex={0} onClick={(event) => { if (event.currentTarget.contains(event.target as Node) && !(event.target as HTMLElement).closest('a,button')) navigate(`/organizations/${kind}/${org.id}`) }} onKeyDown={(event) => { if (event.target === event.currentTarget && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); navigate(`/organizations/${kind}/${org.id}`) } }}><th scope="row"><Link to={`/organizations/${kind}/${org.id}`}>{org.short_name}</Link></th><td>{org.name}</td><td className={styles.actions}><div className={styles.rowMenu}><ItemActionMenu label={t('common.actionsFor', { name: org.name })} canChange={org.capabilities.can_change} canDelete={org.capabilities.can_delete} adminUrl={org.admin_url} onOpen={() => {}} onTrigger={(element) => { focus.current = element }} onEdit={() => setEditing(org)} onDelete={() => setDeleting(org)} /></div></td></tr>)}</tbody></table></div>
      {!result.count && <p>{t('organization.empty')}</p>}
      <nav className={styles.pagination} aria-label={t('organization.pagination')}><Button variant="ghost" disabled={!result.previous} onClick={() => update({ offset: String(Math.max(0, offset - limit)) })}>{t('common.previous')}</Button><span>{t('common.pageOf', { page: Math.floor(offset / limit) + 1, pages: Math.max(1, Math.ceil(result.count / limit)) })}</span><Button variant="ghost" disabled={!result.next} onClick={() => update({ offset: String(offset + limit) })}>{t('common.next')}</Button></nav>
    </section>}
    {editing !== null && <OrganizationFormSheet kind={kind} organization={editing === 'add' ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); setRevision((value) => value + 1) }} returnFocus={focus} />}
    {deleting && <ConfirmDialog title={t('organization.deleteTitle')} description={t('organization.deleteDescription', { name: deleting.name })} pending={mutation.pending} error={mutationError && <Alert tone="danger">{[...mutationError.messages, ...Object.values(mutationError.fields).flat()].join(' ')}</Alert>} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={focus} />}
  </>
}
