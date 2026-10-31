import { ContractSection } from './ContractSection';
import { useEmployeeDetail } from './employeeDetailContext';

/** Show an Employee’s Contracts and their contextual actions. */
export function EmployeeContracts() {
  const { employeeId, refreshEmployee } = useEmployeeDetail();
  return (
    <ContractSection
      scope={{ employeeId }}
      onEmployeeEndDateChange={refreshEmployee}
    />
  );
}
