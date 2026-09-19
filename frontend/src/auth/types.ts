export type Capabilities = {
  view_employee_list: boolean
  view_team_list: boolean
  view_contract_list: boolean
  view_project_list: boolean
  view_organizations: boolean
  view_calendar: boolean
  view_dashboard: boolean
  use_fund_finder: boolean
  import_data: boolean
}

export type AuthenticatedUser = {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  is_authenticated: true
  is_staff: boolean
  is_superuser: boolean
  capabilities: Capabilities
}

export type CurrentUser = AuthenticatedUser | { is_authenticated: false }

export type LoginCredentials = { login: string; password: string }
export type AuthenticationState = { is_authenticated: boolean }
