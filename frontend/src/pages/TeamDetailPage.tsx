import { ArrowLeft, Plus } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate, useParams } from 'react-router-dom'
import { getTeam, getTeamBudgets, getTeamProjects, removeTeamMate, type Team, type TeamBudget, type TeamEmployee, type TeamMate, type TeamProject } from '../api/teams'
import { ApiError, normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { GenericNotes } from '../components/GenericNotes'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { EntityActionMenu } from '../components/EntityActionMenu'
import { ObjectPreferenceActions } from '../components/ObjectPreferenceActions'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { ActivityStatusBadge } from '../ui/ActivityStatusBadge'
import { ProjectCalendarPanel } from './ProjectCalendarPanel'
import { TeamFormSheet } from './TeamFormSheet'
import { TeamMateSheet } from './TeamMateSheet'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeDetailPage.module.css'
import teamStyles from './TeamDetailPage.module.css'

const sections = [
  { path: '', label: 'team.information' },
  { path: 'leaves', label: 'team.leaves' },
  { path: 'projects', label: 'team.projects' },
  { path: 'budget', label: 'team.budget' },
  { path: 'notes', label: 'team.notes' },
] as const

function EmployeeLink({ employee }: { employee: TeamEmployee }) {
  return employee.can_view ? <Link to={`/employees/${employee.id}`}>{employee.name}</Link> : <span>{employee.name}</span>
}

export function TeamDetailPage() {
  const { t } = useTranslation()
  const { teamId = '' } = useParams()
  const location = useLocation()
  const team = useEmployeeResource(teamId, getTeam)
  const tab = location.pathname.split('/').filter(Boolean).at(-1)
  const selected = sections.some((section) => section.path === tab) ? tab : ''
  if (team.loading) return <LoadingState message={t('team.loading')} />
  if (team.error || !team.data) return <div className={styles.mainError}><Alert tone="danger">{team.error instanceof ApiError && team.error.status === 404 ? t('team.notFound') : t('team.loadError')}</Alert><Button onClick={team.retry}>{t('common.retry')}</Button></div>
  return <>
    <Link className={styles.back} to={`/teams/${typeof location.state?.teamListSearch === 'string' && location.state.teamListSearch ? `?${location.state.teamListSearch}` : ''}`}><ArrowLeft aria-hidden="true" />{t('team.back')}</Link>
    <PageHeader title={team.data.name} actions={<div className="flex items-center gap-2"><ObjectPreferenceActions key={team.data.id} type="team" objectId={team.data.id} /><EntityActionMenu label={t('common.actionsFor', { name: team.data.name })} groups={[]} adminUrl={team.data.admin_url} /></div>} />
    <nav aria-label={t('team.navigation')} className={styles.resourceNav}><div className={styles.resourceNavScroll} tabIndex={0}>{sections.map((section) => <NavLink end key={section.path} to={section.path ? `/teams/${teamId}/${section.path}` : `/teams/${teamId}`} state={location.state} className={section.path === selected ? `${styles.resourceLink} ${styles.resourceLinkActive}` : styles.resourceLink}>{t(section.label)}</NavLink>)}</div></nav>
    <div className={styles.panel}>{selected === 'leaves' ? <ProjectCalendarPanel teamId={teamId} /> : selected === 'projects' ? <TeamProjectsPanel teamId={teamId} /> : selected === 'budget' ? <TeamBudgetPanel teamId={teamId} /> : selected === 'notes' ? <GenericNotes scope="team" objectId={teamId} /> : <TeamInformation teamId={teamId} team={team.data} refresh={() => void team.refresh()} />}</div>
  </>
}

function TeamInformation({ teamId, team, refresh }: { teamId: string; team: Team; refresh: () => void }) {
  const { t, language } = useTranslation()
  const navigate = useNavigate()
  const [editingTeam, setEditingTeam] = useState(false)
  const [editingMate, setEditingMate] = useState<TeamMate | null | 'add'>(null)
  const [deleting, setDeleting] = useState<TeamMate | null>(null)
  const focus = useRef<HTMLElement | null>(null)
  const section = useRef<HTMLElement | null>(null)
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    if (!deleting) return
    const result = await mutation.run(() => removeTeamMate(teamId, deleting.id))
    if (result) { focus.current = section.current; setDeleting(null); refresh() }
  }
  return <section ref={section} tabIndex={-1} className={teamStyles.layout}>
    <div className={teamStyles.information}>
      <div className={teamStyles.heading}><h2>{t('team.information')}</h2>{team.capabilities.can_change && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditingTeam(true) }}>{t('common.edit')}</Button>}</div>
      <dl className={teamStyles.facts}><div><dt>{t('team.name')}</dt><dd>{team.name}</dd></div><div><dt>{t('team.leader')}</dt><dd><EmployeeLink employee={team.leader} /></dd></div></dl>
    </div>
    <div className={teamStyles.members}>
      <div className={teamStyles.heading}><h2>{t('team.members')}</h2>{team.capabilities.can_manage_composition && <Button size="sm" variant="secondary" onClick={(event) => { focus.current = event.currentTarget; setEditingMate('add') }}><Plus aria-hidden="true" />{t('team.addMember')}</Button>}</div>
      {team.mates.length ? <div className={teamStyles.memberList}>
        <div className={teamStyles.columnHead} aria-hidden="true"><span>{t('projectCalendar.employee')}</span><span>{t('team.startDate')}</span><span>{t('team.endDate')}</span><span>{t('team.status')}</span><span /></div>
        {team.mates.map((mate) => <div key={mate.id} className={teamStyles.memberRow}>
          <div className={teamStyles.employee}><EmployeeLink employee={mate.employee} /></div>
          <div><span className={teamStyles.mobileLabel}>{t('team.startDate')}: </span>{date(mate.start_date, language)}</div>
          <div><span className={teamStyles.mobileLabel}>{t('team.endDate')}: </span>{date(mate.end_date, language)}</div>
          <div><span className={teamStyles.mobileLabel}>{t('team.status')}: </span><ActivityStatusBadge active={mate.is_active} /></div>
          <div className={teamStyles.actions}><ItemActionMenu label={t('common.actionsFor', { name: mate.employee.name })} canChange={mate.capabilities.can_change} canDelete={mate.capabilities.can_delete} adminUrl={mate.admin_url} onOpen={() => {}} onEdit={() => setEditingMate(mate)} onTrigger={(trigger) => { focus.current = trigger }} onDelete={() => setDeleting(mate)} /></div>
        </div>)}
      </div> : <p>{t('team.noMembers')}</p>}
    </div>
    {editingTeam && <TeamFormSheet team={team} onClose={() => setEditingTeam(false)} onSaved={(saved) => { setEditingTeam(false); if (saved.capabilities.can_view) refresh(); else navigate('/teams/') }} returnFocus={focus} />}
    {editingMate !== null && <TeamMateSheet teamId={teamId} mate={editingMate === 'add' ? null : editingMate} excludedEmployeeIds={[team.leader.id, ...team.mates.filter((mate) => editingMate === 'add' || mate.id !== editingMate.id).map((mate) => mate.employee.id)]} onClose={() => setEditingMate(null)} onSaved={() => { setEditingMate(null); refresh() }} returnFocus={focus} />}
    {deleting && <ConfirmDialog title={t('team.removeMember')} description={t('team.removeConfirm', { name: deleting.employee.name })} pending={mutation.pending} error={error && <Alert tone="danger">{[...error.messages, ...Object.values(error.fields).flat()].join(' ')}</Alert>} onCancel={() => setDeleting(null)} onConfirm={() => void remove()} returnFocus={focus} />}
  </section>
}

function TeamProjectsPanel({ teamId }: { teamId: string }) {
  const { t, language } = useTranslation()
  const resource = useEmployeeResource(teamId, getTeamProjects)
  if (resource.loading) return <LoadingState message={t('team.loading')} />
  if (resource.error) return <Alert tone="danger">{t('team.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  return <section><h2 className={styles.overviewHeading}>{t('team.projects')}</h2>{resource.data?.length ? <div className={styles.tableScroll}><table><thead><tr><th>{t('employee.project')}</th><th>{t('project.columnStart')}</th><th>{t('project.columnEnd')}</th><th>{t('project.columnStatus')}</th></tr></thead><tbody>{resource.data.map((project: TeamProject) => <tr key={project.id}><th><Link to={`/projects/${project.id}`}>{project.name}</Link></th><td>{date(project.start_date, language)}</td><td>{date(project.end_date, language)}</td><td>{t(project.status ? 'filters.active' : 'filters.inactive')}</td></tr>)}</tbody></table></div> : <p>{t('team.noProjects')}</p>}</section>
}

const date = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(new Date(`${value}T12:00:00`)) : '—'
const money = (value: string | null, language: string) => value === null ? '—' : new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))

function TeamBudgetPanel({ teamId }: { teamId: string }) {
  const { t, language } = useTranslation()
  const resource = useEmployeeResource(teamId, getTeamBudgets)
  if (resource.loading) return <LoadingState message={t('team.loading')} />
  if (resource.error) return <Alert tone="danger">{t('team.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button></Alert>
  return <section><h2 className={styles.overviewHeading}>{t('team.budget')}</h2>{resource.data?.length ? <div className={styles.tableScroll}><table><thead><tr><th>{t('employee.project')}</th><th>{t('projectBudgets.fund')}</th><th>{t('projectBudgets.description')}</th><th>{t('team.amount')}</th><th>{t('team.expense')}</th><th>{t('team.available')}</th></tr></thead><tbody>{resource.data.map((budget: TeamBudget) => <tr key={budget.id}><th><Link to={`/projects/${budget.project.id}`}>{budget.project.name}</Link></th><td>{budget.fund.name}</td><td>{budget.cost_type?.short_name} {budget.desc}</td><td>{money(budget.amount, language)}</td><td>{money(budget.expense, language)}</td><td>{money(budget.available, language)}</td></tr>)}</tbody></table></div> : <p>{t('team.noBudgets')}</p>}</section>
}
