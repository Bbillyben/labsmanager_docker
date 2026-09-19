import type { AuthenticatedUser } from '../auth/types'

export const authenticatedUser: AuthenticatedUser = {
  id: 7,
  username: 'ada',
  first_name: 'Ada',
  last_name: 'Lovelace',
  email: 'ada@example.test',
  is_authenticated: true,
  is_staff: false,
  is_superuser: false,
  capabilities: {
    view_employee_list: true,
    view_team_list: false,
    view_contract_list: false,
    view_project_list: true,
    view_organizations: false,
    view_calendar: true,
    view_dashboard: true,
    use_fund_finder: false,
    import_data: false,
  },
}

export const userWithoutNavigationCapabilities: AuthenticatedUser = {
  ...authenticatedUser,
  capabilities: Object.fromEntries(
    Object.keys(authenticatedUser.capabilities).map((capability) => [capability, false]),
  ) as AuthenticatedUser['capabilities'],
}

export function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}
