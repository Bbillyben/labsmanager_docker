import { ApiError } from '../api/errors'
import { getTeam, getTeams, readTeamParams } from '../api/teams'
import { filterDefaultsMarker } from '../filters/url'
import type { EntitySources } from '../filters/types'

export const teamFilterSources = {
  teams: {
    async search(search, signal) {
      const query = new URLSearchParams({ name: search, limit: '10', [filterDefaultsMarker]: '1' })
      const response = await getTeams(readTeamParams(query), signal)
      return {
        options: response.results.map((team) => ({ value: String(team.id), label: team.name })),
        hasMore: response.next !== null,
      }
    },
    async resolve(id, signal) {
      try {
        const team = await getTeam(id, signal)
        return { value: String(team.id), label: team.name }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  },
} satisfies EntitySources
