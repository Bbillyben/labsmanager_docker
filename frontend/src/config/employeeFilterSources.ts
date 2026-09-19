import { getEmployee, getEmployees, readEmployeeParams } from '../api/employees'
import { ApiError } from '../api/errors'
import type { EntitySources } from '../filters/types'

export const employeeFilterSources = {
  employees: {
    async search(search, signal) {
      const query = new URLSearchParams({ search, limit: '10' })
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
  },
} satisfies EntitySources
