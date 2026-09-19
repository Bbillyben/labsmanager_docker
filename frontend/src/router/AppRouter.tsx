import { Route, Routes } from 'react-router-dom'
import { RequireAuth } from '../auth/RequireAuth'
import { AppShell } from '../components/AppShell'
import { HomePage } from '../pages/HomePage'
import { EmployeeListPage } from '../pages/EmployeeListPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'

export function AppRouter() {
  return <Routes><Route path="login" element={<LoginPage />} /><Route element={<RequireAuth />}><Route element={<AppShell />}><Route index element={<HomePage />} /><Route path="employees/" element={<EmployeeListPage />} /></Route><Route path="*" element={<NotFoundPage />} /></Route></Routes>
}
