import { createEmployeeGenericInfo, deleteEmployeeGenericInfo, getEmployeeGenericInfo, getGenericInfoTypes, updateEmployeeGenericInfo } from '../api/employees'
import { GenericInfoSection } from './GenericInfoSection'
import type { GenericInfoApi } from './genericInfoContext'
import { useEmployeeResource } from './useEmployeeResource'

export function EmployeeGenericInfo({ employeeId }: { employeeId: string }) {
  const resource = useEmployeeResource(employeeId, getEmployeeGenericInfo)
  const api: GenericInfoApi = {
    types: getGenericInfoTypes,
    create: (value) => createEmployeeGenericInfo(employeeId, value),
    update: (itemId, value) => updateEmployeeGenericInfo(employeeId, itemId, value),
    delete: (itemId) => deleteEmployeeGenericInfo(employeeId, itemId),
  }
  return <GenericInfoSection data={resource.data} loading={resource.loading} error={resource.error} retry={resource.retry}
    refreshing={resource.refreshing} refreshError={resource.refreshError} refresh={resource.refresh} update={resource.updateData} api={api} />
}
