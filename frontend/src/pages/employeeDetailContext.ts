import { createContext, useContext } from 'react'
import type { EmployeeDetail } from '../api/employees'

export type EmployeeDetailContextValue = { employee: EmployeeDetail; employeeId: string }
export const EmployeeDetailContext = createContext<EmployeeDetailContextValue | null>(null)

export function useEmployeeDetail() {
  const context = useContext(EmployeeDetailContext)
  if (!context) throw new Error('useEmployeeDetail must be used inside EmployeeDetailPage')
  return context
}
