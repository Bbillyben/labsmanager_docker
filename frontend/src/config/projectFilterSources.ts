import { ApiError } from '../api/errors'
import { getProject, getProjects, readProjectParams } from '../api/projects'
import { filterDefaultsMarker } from '../filters/url'
import type { EntitySources } from '../filters/types'

export const projectFilterSources = {
  projects: {
    async search(search, signal) {
      const query = new URLSearchParams({ search, limit: '10', [filterDefaultsMarker]: '1' })
      const response = await getProjects(readProjectParams(query), signal)
      return {
        options: response.results.map((project) => ({ value: String(project.id), label: project.name })),
        hasMore: response.next !== null,
      }
    },
    async resolve(id, signal) {
      try {
        const project = await getProject(id, signal)
        return { value: String(project.id), label: project.name }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  },
} satisfies EntitySources
