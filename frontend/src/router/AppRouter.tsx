import { Route, Routes, useParams } from 'react-router-dom'
import { RequireAuth } from '../auth/RequireAuth'
import { AppShell } from '../components/AppShell'
import { HomePage } from '../pages/HomePage'
import { EmployeeListPage } from '../pages/EmployeeListPage'
import { ProjectListPage } from '../pages/ProjectListPage'
import { TeamListPage } from '../pages/TeamListPage'
import { TeamDetailPage } from '../pages/TeamDetailPage'
import { ContractHubPage } from '../pages/ContractHubPage'
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

function EmployeeNotes() {
  const { employeeId = '' } = useParams()
  return <GenericNotes scope="employee" objectId={employeeId} />
}

export function AppRouter() {
  return <Routes><Route path="login" element={<LoginPage />} /><Route element={<RequireAuth />}><Route element={<AppShell />}><Route index element={<HomePage />} /><Route path="employees/" element={<EmployeeListPage />} /><Route path="tools/contracts" element={<ContractHubPage />} /><Route path="teams/" element={<TeamListPage />} /><Route path="teams/:teamId" element={<TeamDetailPage />} /><Route path="teams/:teamId/leaves" element={<TeamDetailPage />} /><Route path="teams/:teamId/projects" element={<TeamDetailPage />} /><Route path="teams/:teamId/budget" element={<TeamDetailPage />} /><Route path="teams/:teamId/notes" element={<TeamDetailPage />} /><Route path="projects/" element={<ProjectListPage />} /><Route path="projects/:projectId" element={<ProjectDetailPage />} /><Route path="projects/:projectId/tasks" element={<ProjectDetailPage />} /><Route path="projects/:projectId/calendar" element={<ProjectDetailPage />} /><Route path="projects/:projectId/funding" element={<ProjectDetailPage />} /><Route path="projects/:projectId/budgets" element={<ProjectDetailPage />} /><Route path="projects/:projectId/contributions" element={<ProjectDetailPage />} /><Route path="projects/:projectId/contracts" element={<ProjectDetailPage />} /><Route path="projects/:projectId/notes" element={<ProjectDetailPage />} /><Route path="employees/:employeeId" element={<EmployeeDetailPage />}><Route index element={<EmployeeOverview />} /><Route path="projects" element={<EmployeeProjects />} /><Route path="contracts" element={<EmployeeContracts />} /><Route path="funding" element={<EmployeeFunding />} /><Route path="leaves" element={<EmployeeLeaves />} /><Route path="notes" element={<EmployeeNotes />} /></Route></Route><Route path="*" element={<NotFoundPage />} /></Route></Routes>
}
