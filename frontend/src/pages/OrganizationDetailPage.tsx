import { ArrowLeft, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  deleteContact, deleteContactInfo, deleteOrganization, deleteOrganizationInfo, getContactInfos, getContacts,
  getOrganization, getOrganizationContracts, getOrganizationInfos, getOrganizationOptions,
  getOrganizationProjects, getOrganizationSummary,
  type Contact, type OrganizationInfo, type OrganizationKind, type OrganizationOptions,
} from '../api/organizations'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { GenericNotes } from '../components/GenericNotes'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { TypedInfoValue } from '../components/TypedInfoValue'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { EntityActionMenu } from '../components/EntityActionMenu'
import { ObjectPreferenceActions } from '../components/ObjectPreferenceActions'
import { LoadingState } from '../components/LoadingState'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { genericInfoIcon } from './genericInfoIcons'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { OrganizationFormSheet, ContactFormSheet, InfoFormSheet } from './OrganizationSheets'
import { useEmployeeResource } from './useEmployeeResource'
import { getContract } from '../api/contracts'
import { useTrackRecent } from '../hooks/useTrackRecent'
import { ContractDetail } from './ContractDetail'
import { ContractHubTable } from './ContractHubTable'
import { ProjectListTable } from './ProjectListTable'
import styles from './EmployeeDetailPage.module.css'

const tabs = [
  { path: '', key: 'organization.information' }, { path: 'contacts', key: 'organization.contacts' },
  { path: 'projects', key: 'organization.projects' }, { path: 'contracts', key: 'organization.contracts' },
  { path: 'notes', key: 'organization.notes' },
] as const
const money = (value: string, language: string) => new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))

export function OrganizationDetailPage({ kind }: { kind: OrganizationKind }) {
  const { t } = useTranslation()
  const { organizationId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const loader = useCallback((id: string, signal: AbortSignal) => getOrganization(kind, id, signal), [kind])
  const resource = useEmployeeResource(organizationId, loader)
  useTrackRecent(kind === 'institutions' ? 'institution' : 'funder', Number(organizationId), Boolean(resource.data))
  const tab = location.pathname.split('/').filter(Boolean).at(-1)
  const selected = tabs.some((item) => item.path === tab) ? tab : ''
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const focus = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const mutationError = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    const outcome = await mutation.run(() => deleteOrganization(kind, organizationId))
    if (outcome) navigate(`/organizations/${kind}`)
  }
  if (resource.loading) return <LoadingState message={t('common.loading')} />
  if (resource.error || !resource.data) return <Alert tone="danger">{t('organization.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  const org = resource.data
  const base = `/organizations/${kind}/${organizationId}`
  return <>
    <Link className={styles.back} to={`/organizations/${kind}`}><ArrowLeft aria-hidden="true" />{t('organization.back')}</Link>
    <PageHeader title={org.name} description={org.short_name} actions={<div className="flex items-center gap-2"><ObjectPreferenceActions type={kind === 'institutions' ? 'institution' : 'fund_institution'} objectId={org.id} /><EntityActionMenu label={t('common.actionsFor', { name: org.name })} groups={[[...org.capabilities.can_change ? [{ id: 'edit', label: t('common.edit'), icon: <Pencil aria-hidden="true" />, onSelect: () => setEditing(true) }] : [], ...org.capabilities.can_delete ? [{ id: 'delete', label: t('common.delete'), icon: <Trash2 aria-hidden="true" />, onSelect: () => setDeleting(true) }] : []]]} adminUrl={org.admin_url} onTrigger={(trigger) => { focus.current = trigger }} /></div>} />
    <nav aria-label={t('organization.navigation')} className={styles.resourceNav}><div className={styles.resourceNavScroll} tabIndex={0}>{tabs.map((item) => <NavLink end key={item.path} to={item.path ? `${base}/${item.path}` : base} className={selected === item.path ? `${styles.resourceLink} ${styles.resourceLinkActive}` : styles.resourceLink}>{t(item.key)}</NavLink>)}</div></nav>
    <div className={styles.panel}>{selected === 'contacts' ? <ContactsPanel kind={kind} organizationId={organizationId} /> : selected === 'projects' ? <ProjectsPanel kind={kind} organizationId={organizationId} /> : selected === 'contracts' ? <ContractsPanel kind={kind} organizationId={organizationId} /> : selected === 'notes' ? <GenericNotes scope={kind === 'institutions' ? 'institution' : 'funder'} objectId={organizationId} /> : <InformationPanel kind={kind} organizationId={organizationId} name={org.name} shortName={org.short_name} />}</div>
    {editing && <OrganizationFormSheet kind={kind} organization={org} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); void resource.refresh() }} returnFocus={focus} />}
    {deleting && <ConfirmDialog title={t('organization.deleteTitle')} description={t('organization.deleteDescription', { name: org.name })} pending={mutation.pending} error={mutationError && <Alert tone="danger">{[...mutationError.messages, ...Object.values(mutationError.fields).flat()].join(' ')}</Alert>} onCancel={() => setDeleting(false)} onConfirm={() => void remove()} returnFocus={focus} />}
  </>
}

function useOptions(kind: OrganizationKind, organizationId: string) {
  const loader = useCallback((id: string, signal: AbortSignal) => getOrganizationOptions(kind, id, signal), [kind])
  return useEmployeeResource(organizationId, loader)
}

function InformationPanel({ kind, organizationId, name, shortName }: { kind: OrganizationKind; organizationId: string; name: string; shortName: string }) {
  const { t, language } = useTranslation()
  const options = useOptions(kind, organizationId)
  const summaryLoader = useCallback((id: string, signal: AbortSignal) => getOrganizationSummary(kind, id, signal), [kind])
  const summary = useEmployeeResource(organizationId, summaryLoader)
  return <div className="grid gap-6">
    <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section><h2 className={styles.overviewHeading}>{t('organization.general')}</h2><dl className="grid gap-2"><div><dt className="text-sm text-muted-foreground">{t('organization.name')}</dt><dd>{name}</dd></div><div><dt className="text-sm text-muted-foreground">{t('organization.shortName')}</dt><dd>{shortName}</dd></div></dl></section>
      <section className="grid content-start gap-5"><h2 className={styles.overviewHeading}>{t('organization.involvement')}</h2>
        <div><h3 className="mb-3 font-semibold">{t('organization.projectSummary')}</h3>{summary.data ? <dl className="grid gap-3 sm:grid-cols-2"><Metric label={t('organization.totalProjects')} value={summary.data.projects.total} /><Metric label={t('organization.openProjects')} value={summary.data.projects.open} /><Metric label={t('organization.totalAmount')} value={money(summary.data.projects.total_amount, language)} /><Metric label={t('organization.availableAmount')} value={money(summary.data.projects.available_amount, language)} /><Metric label={t('organization.availableFocus')} value={money(summary.data.projects.available_amount_focus, language)} /></dl> : summary.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : <LoadingState message={t('common.loading')} />}</div>
        <div><h3 className="mb-3 font-semibold">{t('organization.contractSummary')}</h3>{summary.data ? <dl className="grid gap-3 sm:grid-cols-2"><Metric label={t('organization.totalContracts')} value={summary.data.contracts.total} /><Metric label={t('organization.currentContracts')} value={summary.data.contracts.current} /><Metric label={t('organization.activeContracts')} value={summary.data.contracts.active} /><Metric label={t('organization.manMonths')} value={summary.data.contracts.man_months} /></dl> : summary.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : <LoadingState message={t('common.loading')} />}</div>
      </section>
    </div>
    {options.data ? <InfoCollection kind={kind} organizationId={organizationId} options={options.data} /> : options.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : <LoadingState message={t('common.loading')} />}
  </div>
}
function Metric({ label, value }: { label: string; value: string | number }) { return <div className="border-l border-border pl-3"><dt className="text-sm text-muted-foreground">{label}</dt><dd className="font-semibold">{value}</dd></div> }

type InfoCollectionProps = { kind: OrganizationKind; organizationId: string; options: OrganizationOptions; contactId?: number }
function InfoCollection({ kind, organizationId, options, contactId }: InfoCollectionProps) {
  const { t } = useTranslation()
  const loader = useCallback((id: string, signal: AbortSignal) => contactId === undefined ? getOrganizationInfos(kind, id, signal) : getContactInfos(kind, id, contactId, signal), [kind, contactId])
  const resource = useEmployeeResource(organizationId, loader)
  const [editing, setEditing] = useState<OrganizationInfo | null | 'add'>(null)
  const [deleting, setDeleting] = useState<OrganizationInfo | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const mutationError = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    if (!deleting) return
    const outcome = await mutation.run(() => contactId === undefined ? deleteOrganizationInfo(kind, organizationId, deleting.id) : deleteContactInfo(kind, organizationId, contactId, deleting.id))
    if (outcome) { setDeleting(null); void resource.refresh() }
  }
  return <section><div className="flex flex-wrap items-center justify-between gap-2"><h2 className={styles.overviewHeading}>{t('organization.infos')}</h2>{resource.data?.capabilities.can_add && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditing('add') }}><Plus aria-hidden="true" />{t('organization.addInfo')}</Button>}</div>
    {resource.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : !resource.data ? <LoadingState message={t('common.loading')} /> : resource.data.items.length ? <ul className="divide-y divide-border">{resource.data.items.map((item) => { const Icon = genericInfoIcon(item.info.icon); return <li key={item.id} className="flex items-center gap-3 py-3"><Icon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" /><div className="min-w-0 flex-1"><p className="font-medium">{item.info.name}</p><TypedInfoValue kind={item.info.type} value={item.value} mapProvider={options.map_provider} />{item.comment && <p className="text-sm text-muted-foreground">{item.comment}</p>}</div><ItemActionMenu label={t('common.actionsFor', { name: item.info.name })} canChange={item.capabilities.can_change} canDelete={item.capabilities.can_delete} adminUrl={item.admin_url} onOpen={() => {}} onTrigger={(trigger) => { focus.current = trigger }} onEdit={() => setEditing(item)} onDelete={() => setDeleting(item)} /></li> })}</ul> : <p>{t('organization.noInfos')}</p>}
    {editing !== null && <InfoFormSheet kind={kind} organizationId={organizationId} contactId={contactId} item={editing === 'add' ? null : editing} options={options} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); void resource.refresh() }} returnFocus={focus} />}
    {deleting && <ConfirmDialog title={t('organization.deleteInfo')} description={t('organization.deleteDescription', { name: deleting.info.name })} pending={mutation.pending} error={mutationError && <Alert tone="danger">{[...mutationError.messages, ...Object.values(mutationError.fields).flat()].join(' ')}</Alert>} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={focus} />}
  </section>
}

function ContactsPanel({ kind, organizationId }: { kind: OrganizationKind; organizationId: string }) {
  const { t } = useTranslation()
  const options = useOptions(kind, organizationId)
  const loader = useCallback((id: string, signal: AbortSignal) => getContacts(kind, id, signal), [kind])
  const resource = useEmployeeResource(organizationId, loader)
  const [selected, setSelected] = useState<Contact | null>(null)
  const [editing, setEditing] = useState<Contact | null | 'add'>(null)
  const [deleting, setDeleting] = useState<Contact | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const mutationError = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    if (!deleting) return
    const outcome = await mutation.run(() => deleteContact(kind, organizationId, deleting.id))
    if (outcome) { setDeleting(null); setSelected(null); void resource.refresh() }
  }
  return <section><div className="flex flex-wrap items-center justify-between gap-2"><h2 className={styles.overviewHeading}>{t('organization.contacts')}</h2>{resource.data?.capabilities.can_add && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditing('add') }}><Plus aria-hidden="true" />{t('organization.addContact')}</Button>}</div>
    {resource.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : !resource.data ? <LoadingState message={t('common.loading')} /> : resource.data.items.length ? <ul className="divide-y divide-border">{resource.data.items.map((contact) => <li key={contact.id} className="flex items-center gap-3 py-3"><Button variant="ghost" className="flex-1 justify-start" onClick={(event) => { focus.current = event.currentTarget; setSelected(contact) }}>{contact.first_name} {contact.last_name}<span className="ml-2 text-sm text-muted-foreground">{contact.type.name}</span></Button><ItemActionMenu label={t('common.actionsFor', { name: `${contact.first_name} ${contact.last_name}` })} canChange={contact.capabilities.can_change} canDelete={contact.capabilities.can_delete} adminUrl={contact.admin_url} onOpen={() => {}} onTrigger={(trigger) => { focus.current = trigger }} onEdit={() => { setSelected(null); setEditing(contact) }} onDelete={() => { setSelected(null); setDeleting(contact) }} /></li>)}</ul> : <p>{t('organization.noContacts')}</p>}
    {selected && options.data && <Sheet open onOpenChange={(open) => { if (!open) setSelected(null) }}><SheetContent finalFocus={focus}><SheetHeader><SheetTitle>{selected.first_name} {selected.last_name}</SheetTitle><SheetDescription>{selected.type.name}</SheetDescription></SheetHeader><p>{selected.comment}</p><div className="mt-4"><InfoCollection kind={kind} organizationId={organizationId} contactId={selected.id} options={options.data} /></div>{selected.capabilities.can_change && <Button variant="secondary" onClick={() => { setEditing(selected); setSelected(null) }}><Pencil aria-hidden="true" />{t('common.edit')}</Button>}</SheetContent></Sheet>}
    {editing !== null && options.data && <ContactFormSheet kind={kind} organizationId={organizationId} contact={editing === 'add' ? null : editing} options={options.data} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); void resource.refresh() }} returnFocus={focus} />}
    {deleting && <ConfirmDialog title={t('organization.deleteContact')} description={t('organization.deleteDescription', { name: `${deleting.first_name} ${deleting.last_name}` })} pending={mutation.pending} error={mutationError && <Alert tone="danger">{[...mutationError.messages, ...Object.values(mutationError.fields).flat()].join(' ')}</Alert>} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={focus} />}
  </section>
}

function ProjectsPanel({ kind, organizationId }: { kind: OrganizationKind; organizationId: string }) {
  const { t } = useTranslation()
  const loader = useCallback((id: string, signal: AbortSignal) => getOrganizationProjects(kind, id, signal), [kind])
  const resource = useEmployeeResource(organizationId, loader)
  return <section><h2 className={styles.overviewHeading}>{t('organization.projects')}</h2>{resource.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : !resource.data ? <LoadingState message={t('common.loading')} /> : resource.data.length ? <ProjectListTable projects={resource.data} /> : <p>{t('organization.noProjects')}</p>}</section>
}

function ContractsPanel({ kind, organizationId }: { kind: OrganizationKind; organizationId: string }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<number | null>(null)
  const loader = useCallback((id: string, signal: AbortSignal) => getOrganizationContracts(kind, id, signal), [kind])
  const resource = useEmployeeResource(organizationId, loader)
  return <section><h2 className={styles.overviewHeading}>{t('organization.contracts')}</h2>{resource.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : !resource.data ? <LoadingState message={t('common.loading')} /> : resource.data.length ? <ContractHubTable items={resource.data} selectedId={selected} onSelect={setSelected} onNotesClosed={() => { void resource.refresh() }} /> : <p>{t('organization.noContracts')}</p>}{selected !== null && <SelectedContract id={selected} />}</section>
}

function SelectedContract({ id }: { id: number }) {
  const loader = useCallback((_id: string, signal: AbortSignal) => getContract({ hubContractId: id }, id, signal), [id])
  const resource = useEmployeeResource(String(id), loader)
  const { t } = useTranslation()
  return resource.data ? <ContractDetail contract={resource.data} /> : resource.error ? <Alert tone="danger">{t('organization.loadError')}</Alert> : <LoadingState message={t('common.loading')} />
}
