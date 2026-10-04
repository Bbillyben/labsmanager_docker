import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useParams } from 'react-router-dom'
import { RequireAuth } from '../auth/RequireAuth'
import { AppShell } from '../components/AppShell'
import { HomePage } from '../pages/HomePage'
import { EmployeeListPage } from '../pages/EmployeeListPage'
import { ProjectListPage } from '../pages/ProjectListPage'
import { TeamListPage } from '../pages/TeamListPage'
import { TeamDetailPage } from '../pages/TeamDetailPage'
import { ContractHubPage } from '../pages/ContractHubPage'
import { FinancialToolPage } from '../pages/FinancialToolPage'
import { ImportPage } from '../pages/ImportPage'
import { GlobalCalendarsPage } from '../pages/GlobalCalendarsPage'
import { SettingsHubPage, UserAccountSection, UserPreferencesSection, UserSettingsSection } from '../pages/SettingsHubPage'
import { MutableListGroupPage } from '../pages/MutableListPage'
import { AdminSettingsSection, AdminUsersPage, AdminNotificationsPage, AdminPluginsPage, AdminPluginDetailPage } from '../pages/AdminSettingsPage'
import { useAuth } from '../auth/AuthContext'
import { ProjectDetailPage } from '../pages/ProjectDetailPage'
import { EmployeeDetailPage } from '../pages/EmployeeDetailPage'
import { EmployeeContracts } from '../pages/EmployeeContracts'
import { EmployeeFunding } from '../pages/EmployeeFunding'
import { EmployeeLeaves } from '../pages/EmployeeLeaves'
import { GenericNotes } from '../components/GenericNotes'
import { EmployeeOverview } from '../pages/EmployeeOverview'
import { EmployeeProjects } from '../pages/EmployeeProjects'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OrganizationListPage } from '../pages/OrganizationListPage'
import { OrganizationDetailPage } from '../pages/OrganizationDetailPage'
import { LoadingState } from '../components/LoadingState'
import { useTranslation } from '../i18n/i18n'
import { PrintProvider } from '../print/PrintProvider'
import { SearchPage } from '../search/SearchPage'

const OrganizationChartPage = lazy(() => import('../pages/OrganizationChartPage').then((module) => ({ default: module.OrganizationChartPage })))
const DashboardPage = lazy(() => import('../dashboard/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const DashboardPresentation = lazy(() => import('../dashboard/DashboardPresentation').then((module) => ({ default: module.DashboardPresentation })))

function OrganizationChartRoute() {
  const { t } = useTranslation()
  return <Suspense fallback={<LoadingState message={t('common.loading')} />}><OrganizationChartPage /></Suspense>
}

function DashboardRoute() {
  const { t } = useTranslation()
  return <Suspense fallback={<LoadingState message={t('common.loading')} />}><DashboardPage /></Suspense>
}

function DashboardPresentationRoute() {
  const { t } = useTranslation()
  return <Suspense fallback={<LoadingState message={t('common.loading')} />}><DashboardPresentation /></Suspense>
}

function EmployeeNotes() {
  const { employeeId = '' } = useParams()
  return <GenericNotes scope="employee" objectId={employeeId} />
}

function StaffSettingsRoute({ children }: { children: React.ReactNode }) {
  const auth = useAuth()
  return auth.status === 'authenticated' && auth.user.is_staff ? children : <Navigate to="/settings/user" replace />
}

export function AppRouter() {
  return <PrintProvider><Routes><Route path="login" element={<LoginPage />} /><Route element={<RequireAuth />}><Route element={<AppShell />}><Route index element={<HomePage />} /><Route path="search" element={<SearchPage />} /><Route path="dashboard" element={<DashboardRoute />} /><Route path="employees/" element={<EmployeeListPage />} /><Route path="calendars" element={<GlobalCalendarsPage />} /><Route path="settings" element={<SettingsHubPage />}><Route index element={<Navigate to="user" replace />} /><Route path="user" element={<UserAccountSection />} /><Route path="interface" element={<UserSettingsSection section="interface" />} /><Route path="notifications" element={<UserSettingsSection section="notifications" />} /><Route path="common" element={<UserPreferencesSection />} /><Route path="stale" element={<UserSettingsSection section="stale" />} /><Route path="lists/:groupKey" element={<MutableListGroupPage />} /><Route path="admin" element={<StaffSettingsRoute><Outlet /></StaffSettingsRoute>}><Route path="general" element={<AdminSettingsSection section="general" />} /><Route path="users" element={<AdminUsersPage />} /><Route path="notifications" element={<AdminNotificationsPage />} /><Route path="plugins" element={<AdminPluginsPage />} /><Route path="plugins/:pluginKey" element={<AdminPluginDetailPage />} /></Route></Route><Route path="tools/import" element={<ImportPage />} /><Route path="tools/organization-chart" element={<OrganizationChartRoute />} /><Route path="tools/contracts" element={<ContractHubPage />} /><Route path="tools/fund-items" element={<FinancialToolPage kind="fund-items" />} /><Route path="tools/budgets" element={<FinancialToolPage kind="budgets" />} /><Route path="tools/expenses" element={<FinancialToolPage kind="expenses" />} /><Route path="organizations/institutions" element={<OrganizationListPage kind="institutions" />} /><Route path="organizations/funders" element={<OrganizationListPage kind="funders" />} /><Route path="organizations/institutions/:organizationId/*" element={<OrganizationDetailPage kind="institutions" />} /><Route path="organizations/funders/:organizationId/*" element={<OrganizationDetailPage kind="funders" />} /><Route path="teams/" element={<TeamListPage />} /><Route path="teams/:teamId" element={<TeamDetailPage />} /><Route path="teams/:teamId/leaves" element={<TeamDetailPage />} /><Route path="teams/:teamId/projects" element={<TeamDetailPage />} /><Route path="teams/:teamId/budget" element={<TeamDetailPage />} /><Route path="teams/:teamId/notes" element={<TeamDetailPage />} /><Route path="projects/" element={<ProjectListPage />} /><Route path="projects/:projectId" element={<ProjectDetailPage />} /><Route path="projects/:projectId/tasks" element={<ProjectDetailPage />} /><Route path="projects/:projectId/calendar" element={<ProjectDetailPage />} /><Route path="projects/:projectId/funding" element={<ProjectDetailPage />} /><Route path="projects/:projectId/budgets" element={<ProjectDetailPage />} /><Route path="projects/:projectId/contributions" element={<ProjectDetailPage />} /><Route path="projects/:projectId/contracts" element={<ProjectDetailPage />} /><Route path="projects/:projectId/dashboard" element={<ProjectDetailPage />} /><Route path="projects/:projectId/notes" element={<ProjectDetailPage />} /><Route path="employees/:employeeId" element={<EmployeeDetailPage />}><Route index element={<EmployeeOverview />} /><Route path="projects" element={<EmployeeProjects />} /><Route path="contracts" element={<EmployeeContracts />} /><Route path="funding" element={<EmployeeFunding />} /><Route path="leaves" element={<EmployeeLeaves />} /><Route path="notes" element={<EmployeeNotes />} /></Route></Route><Route path="dashboard/:dashboardId/present" element={<DashboardPresentationRoute />} /><Route path="*" element={<NotFoundPage />} /></Route></Routes></PrintProvider>
}
