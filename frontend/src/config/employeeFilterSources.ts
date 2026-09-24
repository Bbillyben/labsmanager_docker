import { getEmployee, getEmployees, readEmployeeParams } from '../api/employees'
import { ApiError } from '../api/errors'
import type { EntitySources } from '../filters/types'

function employeeSource(includeInactive: boolean) {
  return {
    async search(search, signal) {
      const query = new URLSearchParams({ search, limit: '10' })
      if (includeInactive) query.set('filters_initialized', '1')
      const response = await getEmployees(readEmployeeParams(query), signal)
      return {
        options: response.results.map((employee) => ({ value: String(employee.id), label: `${employee.first_name} ${employee.last_name}` })),
        hasMore: response.next !== null,
      }
    },
    async resolve(id, signal) {
      try {
        const employee = await getEmployee(id, signal)
        return { value: String(employee.id), label: `${employee.first_name} ${employee.last_name}` }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  } satisfies EntitySources[string]
}

export const employeeFilterSources = {
  employees: employeeSource(false),
  allEmployees: employeeSource(true),
} satisfies EntitySources
