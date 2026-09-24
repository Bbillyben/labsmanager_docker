import { Route, Routes } from 'react-router-dom'
import { RequireAuth } from '../auth/RequireAuth'
import { AppShell } from '../components/AppShell'
import { HomePage } from '../pages/HomePage'
import { EmployeeListPage } from '../pages/EmployeeListPage'
import { ProjectListPage } from '../pages/ProjectListPage'
import { ProjectSinglePendingPage } from '../pages/ProjectSinglePendingPage'
import { EmployeeDetailPage } from '../pages/EmployeeDetailPage'
import { EmployeeContracts } from '../pages/EmployeeContracts'
import { EmployeeFunding } from '../pages/EmployeeFunding'
import { EmployeeLeaves } from '../pages/EmployeeLeaves'
import { EmployeeFuturePanel } from '../pages/EmployeeFuturePanel'
import { EmployeeOverview } from '../pages/EmployeeOverview'
import { EmployeeProjects } from '../pages/EmployeeProjects'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'

export function AppRouter() {
  return <Routes><Route path="login" element={<LoginPage />} /><Route element={<RequireAuth />}><Route element={<AppShell />}><Route index element={<HomePage />} /><Route path="employees/" element={<EmployeeListPage />} /><Route path="projects/" element={<ProjectListPage />} /><Route path="projects/:projectId" element={<ProjectSinglePendingPage />} /><Route path="employees/:employeeId" element={<EmployeeDetailPage />}><Route index element={<EmployeeOverview />} /><Route path="projects" element={<EmployeeProjects />} /><Route path="contracts" element={<EmployeeContracts />} /><Route path="funding" element={<EmployeeFunding />} /><Route path="leaves" element={<EmployeeLeaves />} /><Route path="notes" element={<EmployeeFuturePanel title="employee.navNotes" />} /></Route></Route><Route path="*" element={<NotFoundPage />} /></Route></Routes>
}
