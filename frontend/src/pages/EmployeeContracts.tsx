import { ContractSection } from './ContractSection'
import { useEmployeeDetail } from './employeeDetailContext'

export function EmployeeContracts() {
  const { employeeId, refreshEmployee } = useEmployeeDetail()
  return <ContractSection scope={{ employeeId }} onEmployeeEndDateChange={refreshEmployee} />
}
