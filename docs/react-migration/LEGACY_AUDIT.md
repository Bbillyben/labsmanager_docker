# Legacy UI Audit

Status: Phase 1 audit

Last updated: 2026-10-11

Scope: Django legacy user-facing UI and related compatibility routes

This inventory supports the end of Phase 1 and preparation of Phase 2. React is the main UI under `/app/`; Django remains the backend. The legacy UI was deliberately retained. **This audit authorizes no removal or redirect**: each change needs parity, browser, caller and compatibility validation. Update the relevant row when a workflow is migrated, redirected or removed.

## 1. Executive summary

The matrix below groups **32 page/workflow families**, not individual modal or AJAX URLs: **27 React fallbacks, 3 compatibility/auth families and 2 undetermined families**. No family is proven safe to remove. The Project Planning bulk delay is now implemented in React with DAG propagation; bulk validation is intentionally dropped. Plugin-supplied custom settings HTML remains deployment-dependent and outside this focused follow-up. These counts exclude the technical Django routes in section 4.

- The legacy navigation still links to its main pages; legacy JavaScript still calls their HTML fragments and mutation modals. A React analogue does not make those endpoints unused.
- Employee/Project reports have a React selection dialog and API, while Django still owns document generation and historical download URLs.
- Notifications use React destinations when configured but explicitly fall back to Employee, Project, Team, Calendar and Settings Django pages. An older report email also links to Employee.
- Allauth, invitation and password-reset bridges, external bookmarks and plugin URLs require separate compatibility checks.
- The Project Planning React table now supports bulk delay with dependency propagation. Legacy bulk validation remains available only in Django and is intentionally not migrated; individual React editing suffices.
- Main React workflows have user browser acceptance. Runtime checks now concern old links, unusual auth screens, plugin extensions and safe redirect/removal, not a blanket revalidation of every React page.

Evidence: `backend/labsmanager/urls.py`, the included app `urls.py` files, `backend/templates/navbar.html`, `backend/templates/labmanager/index_card_tools.html`, `frontend/src/router/AppRouter.tsx`, `backend/labsmanager/email_urls.py` and `backend/data/static/js/`.

## 2. Classification rules

`React fallback` means a React route and principal capability exist but the Django UI remains callable during Phase 1; parity can still be partial. `To migrate` requires an observed user feature with no equivalent React. `Keep Django` is a deliberate backend or administrative workflow. `Compatibility` is retained for old links or auth hand-offs. `Candidate removal` requires adequate React parity **and** no known internal, email, plugin or external caller. `Unknown` requires runtime evidence. `High` confidence means the claim follows directly from routes and callers; `Medium` means functional parity or deployment usage needs checking; `Low` means static inspection cannot decide. User acceptance of the main React journeys is taken as given; a `Partial` row below denotes a specific known difference, not an outdated browser-validation note.

The prefixes `/staff/`, `/project/`, `/fund/`, `/expense/`, `/dashboard/`, `/settings/`, `/milestones/`, `/calendar/`, `/common/`, `/reports/`, `/infos/` and `/import/` are included from `backend/labsmanager/urls.py`; URL names in parentheses are unnamespaced. Most legacy pages use `LoginRequiredMixin`; their object permissions are enforced by their own views. React routes listed below are behind `RequireAuth`, except auth entry points. Do not infer equivalent permission behavior from route existence alone.

## 3. User-facing legacy route matrix

“Legacy shell” means a link in Django navigation or a detail template; “JS” means a concrete `Urls[...]`/AJAX caller in `backend/data/static/js/`. Related modal and fragment routes are grouped with their parent workflow rather than counted as separate pages. View/template evidence is in the cited app `urls.py` and `views.py`, with templates under `backend/templates/`.

| Area | Legacy route/page | Django view/template | React equivalent | Parity | Missing parity / validation | Current callers | Classification | Phase 2 action | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home | `/`, `/index/` (`index`) | `IndexView` / `labmanager/index.html` | `/app/` | Almost complete | Check landing and anonymous redirect behavior | Root URL, legacy shell | React fallback | redirect to React after validation | High |
| Employee list | `/staff/`, `/staff/employee/` (`staff`, `employee_index`) | `EmployeeIndexView` / `employee/employee_base.html` | `/app/employees/` | Almost complete | Browser parity of filters, exports and permissions | Legacy navbar/cards | React fallback | redirect to React | High |
| Employee detail | `/staff/employee/<pk>` (`employee`) | `EmployeeView` / `employee/employee_single.html` | `/app/employees/:id` and subroutes | Complete | Accepted React workflow; fine permission adjustments are not a migration blocker | Legacy tables, emails/fallback, `global_report.html` | React fallback | preserve compatibility route, then redirect | High |
| Employee edit | `/staff/employee/add/`, `/<pk>/udpate`, `/<pk>/delete` | `Employee*View` / modal templates | Employee list/detail Sheets and API | Almost complete | Mutation/browser parity; legacy page still calls modals | Legacy Employee list/detail JS | React fallback | remove modals only with parent UI | High |
| Employee hierarchy/status | `/staff/employee/<id>/superior|subordinate/...`, `/status/...` | `EmployeeSuperior*`, `Status*` / modals | Employee Overview | Complete | Accepted React workflow; legacy modals remain for legacy callers | Legacy Employee JS | React fallback | remove after parent retirement | Medium |
| Employee info/notes | `/staff/employee/<id>/info/add/`, `/infos/notes/...` | `EmployeeInfo*`, `GenericNote*` / fragments | Employee detail info/notes | Complete | Accepted React workflow; legacy fragments remain for legacy callers | Legacy detail JS, notes template | React fallback | remove after parent retirement | Medium |
| Team list | `/staff/team/` (`team_index`) | `TeamIndexView` / `team/team_base.html` | `/app/teams/` | Almost complete | Browser parity | Legacy navbar/cards | React fallback | redirect to React | High |
| Team detail/membership | `/staff/team/<pk>` (`team_single`), TeamMate modals | `TeamView`, `TeamMate*` / `team/team_single.html` | `/app/teams/:id` and subroutes | Partial | Check all legacy panels and edits | Legacy tables, email fallback | React fallback | preserve compatibility route, then redirect | High |
| Organization chart | `/staff/organisation_chart/` | `OrganisationChartView` / `employee/organization_chart.html` | `/app/tools/organization-chart` | Almost complete | Check chart interactions and large hierarchies | Legacy tools card | React fallback | redirect to React | High |
| Project list | `/project/` (`project_index`) | `ProjectIndexView` / `project/project_base.html` | `/app/projects/` | Almost complete | Browser parity of filters/actions | Legacy navbar/cards | React fallback | redirect to React | High |
| Project detail | `/project/<pk>` (`project_single`) | `ProjectView` / `project/project_single.html` | `/app/projects/:id` | Almost complete | Bulk delay implemented; bulk validation intentionally dropped; browser validation of delay pending | Legacy tables, email fallback | React fallback | retain compatibility URL pending browser/caller checks | High |
| Project planning | Project detail planning, `/milestones/...` modals | Project template, milestone modal views | `/app/projects/:id/tasks` | Almost complete | Bulk delay uses dependency DAG; individual CRUD, Gantt and print present; bulk validation intentionally dropped | Project detail JS | React fallback | verify bulk delay in browser before retiring legacy modals | High |
| Project funding | Project detail and `/project/<pk>/fundoverview/`, `/fund/<pk>/...` | Funding HTML fragments in Project/Fund views | `/app/projects/:id/funding` | Complete | Fund graphs reorganized; ordinary Fund/Expense workflow covered | Project detail JS and fragment loaders | React fallback | retire fragments with parent UI | High |
| Project budgets/contributions | `/fund/ajax/budget/...`, `/fund/ajax/contribution/...` | Budget/Contribution modal views | `/app/projects/:id/budgets`, `/contributions` | Complete | Separate sections replace legacy panels | Legacy Project/Fund JS | React fallback | retire modals with parent UI | Medium |
| Project participants/info | `/project/ajax/.../participant/...`, `/project/.../info/...` | Participant/Info modal views | Project overview/detail | Complete | Sheets replace legacy modals, including leader/co-leader and institution roles | Project detail JS | React fallback | retire modals with parent UI | Medium |
| Project calendar | Project detail and `/project/print/` | Project calendar template and print view | `/app/projects/:id/calendar` | Complete | React calendar/list/resources and print exist; historical print URL still needs compatibility check | Project detail UI | React fallback | keep print endpoint until checked | High |
| Contract index | `/expense/` (`contract_index`) | `ContractIndexView` / `expense/contract_base.html` | `/app/tools/contracts` | Almost complete | Browser visibility/export parity | Legacy tools card | React fallback | redirect to React | High |
| Contract/expense modals | `/expense/ajax/contract/...`, `/expense/expense/...` | `Contract*`, `Expense*` / modals and fragments | Project/Employee Contracts, Contract Hub, Expense sections | Partial | Check context-specific mutations and sync | Legacy Contract/Fund/Project JS | React fallback | remove only after caller audit | Medium |
| Fund finder | `/fund/finder` (`fund_finder`) | `FundFinderView` / `fund/fund_finder.html` | Specialized React Fund items, Budget finder and Contract tool | Complete | Replaced differently; no unified finder or 1:1 parity required. Navigation organization is a separate React task. | Legacy tools card | React fallback | decide contextual redirect/navigation, not reimplement finder | High |
| Organization list | `/infos/` (`orga_index`) | `OrganizationIndexView` / `organization/orga_base.html` | `/app/organizations/institutions`, `/funders` | Almost complete | One legacy route needs role-aware target | Legacy navbar | React fallback | route by context or preserve chooser | High |
| Organization detail | `/infos/<app>/<model>/<pk>` (`orga_single`) | `InstitutionView` / `organization/institution_single.html` | Institution/Funder detail routes | Partial | Map model identifiers, contacts and notes | Legacy tables, preferences/serializers | React fallback | preserve role-aware compatibility mapping | High |
| Import | `/import/`, `/import/funditem/`, `/confirm` | `ImportViewBase`, `FundItemImportView` / `import/import_base.html` and fragments | `/app/tools/import` | Almost complete | Compare all resource profiles and import confirmation | Legacy tools card, `import_base.js` | React fallback | redirect UI only; retain downloads/API | High |
| Global calendar | `/calendar/main` (`calendar_main`) | `main_calendar_view` / `calendar/main_calendar.html` | `/app/calendars` | Almost complete | Plugin events, scopes and print browser parity | Legacy navbar, email fallback | React fallback | preserve compatibility route, then redirect | High |
| Dashboard | `/dashboard/` | `DashboardView` / `dashboard/global_dashboard.html` | `/app/dashboard` | Complete | React is the functional reference; legacy dashboard parity is intentionally unnecessary | Legacy navbar; card fragment loaders | React fallback | redirect with old-link compatibility | High |
| User settings | `/settings/` (`settings`) user/interface/notification/dashboard panels | `SettingsView` / `settings/settings.html` and includes | `/app/settings/user`, `/interface`, `/notifications`, `/common`, `/stale` | Partial | Map anchors and verify all settings; email fallback | Legacy navbar, email fallback | React fallback | preserve compatibility route, then redirect | High |
| Admin settings/lists | `/settings/` admin panels and `setting_*` fragments | `SettingsView`, setting list views / `settings/*.html` | `/app/settings/admin/*`, `/lists/:groupKey` | Almost complete | Check all eleven mutable lists and retention setting | Legacy sidebar, settings JS | React fallback | retire fragments with parent UI | Medium |
| Report selection | `/reports/{employee,project}/.../generate/` | `*ReportView` / `form_base.html` modal | Validated `ReportExportDialog` on Employee/Project | Complete | None in selection UI; Django generation/download intentionally retained | Legacy entity action menus | React fallback | remove modal UI only; keep render/download routes | High |
| Account sign-in/email | `/accounts/` allauth HTML screens | Allauth views / `account/*.html` | `/app/login`, Settings account | Partial | Main UI migrated; email confirmation and exceptional inactive/error screens remain Django | Allauth callbacks, legacy account templates | Compatibility | preserve compatibility route | High |
| Password reset | `/accounts/password/reset/...` and bridge | Allauth/bridge views / `account/password_reset*.html` | `/app/password/reset...` | Complete | New React flow exists; old emailed links intentionally remain Django-compatible | Reset emails and auth bridge | Compatibility | preserve compatibility route | High |
| Invitation acceptance | `/invitations/accept/<key>/`, `/accounts/signup/` | `AcceptInvite`, `AtomicInvitationSignupView` / allauth templates | `/app/invitations/accept...` | Complete | New React flow exists; old invited links/signup intentionally remain compatible | Existing invitation emails/tokens | Compatibility | preserve compatibility route | High |
| Organization alias | `/infos/institution/<pk>` (`institution_single`) | `InstitutionView`; expects `app/model` in `get()` | Institution detail | None | Route appears incompatible with view parameters; runtime check | No concrete caller found in inspected code | Unknown | investigate | Medium |
| Legacy dashboard placeholders | `/dashboard/fundloss`, `/fundstale`, `/contractstale` | Placeholder views returning “not yet defined” | Dashboard | None | External caller/history unknown; card variants are active | No internal caller found for placeholder pages | Unknown | investigate before any removal | Medium |

The `/infos/` route split into Institution and Funder must use the record's actual model, not a name-based guess. The old `fund_finder` is replaced by specialized React tools, with no one-to-one target. Remaining `Partial` rows describe specific differences, not the mere presence of legacy code. The matrix combines code inspection with the user's acceptance of the main React journeys; it does not prove historical-link behavior in production.

### Project detail gap analysis

This comparison is limited to the legacy `backend/templates/project/project_single.html`, its Project/milestone modal routes and the React `ProjectDetailPage`, Overview, Planning, Funding, Budgets, Contracts and Calendar panels. **21 capabilities: 13 Implemented, 4 Replaced differently, 1 Backend-only, 1 Legacy artifact, 0 Real gaps, 1 Needs runtime check, 1 Intentionally dropped.** React's accepted main workflow is not reopened merely because the old modals and fragments remain in the legacy shell.

| Legacy capability | React equivalent | Status | Evidence | Decision |
| --- | --- | --- | --- | --- |
| Overview: name, dates, active status and metadata | `ProjectOverview`, `ProjectSheet` | Implemented | `frontend/src/pages/ProjectOverview.tsx`, `ProjectSheet.tsx` | keep React behavior |
| Project edit action and per-page modal | Header menu and Project Sheet | Replaced differently | `frontend/src/pages/ProjectDetailPage.tsx` | keep Sheet; legacy modal is not a gap |
| Participants, including leader/co-leader role, add/edit/delete | `ProjectParticipantBlock` and `ParticipantSheet` | Implemented | `frontend/src/pages/ProjectParticipantBlock.tsx`; `backend/templates/project/project_single.html` | keep React behavior |
| Institution/manager attachments and coordinator role | `ProjectInstitutionBlock` | Implemented | `frontend/src/pages/ProjectInstitutionBlock.tsx` | keep React behavior |
| Generic project information CRUD | `GenericInfoSection` in Overview | Implemented | `frontend/src/pages/ProjectOverview.tsx` | keep React behavior |
| Project notes CRUD | `GenericNotes` Project scope | Implemented | `frontend/src/pages/ProjectDetailPage.tsx` | keep React behavior |
| Task/milestone list and individual create/edit/delete | Planning table, detail and form Sheets | Implemented | `frontend/src/pages/ProjectPlanningPanel.tsx`, `MilestoneDetailSheet.tsx` | keep React behavior |
| **Delay selected open milestones by a number of days** | Project Planning table selection and Delay Sheet with DAG preview/apply | **Implemented** | `frontend/src/pages/ProjectPlanningDelaySheet.tsx`; `backend/endpoints/delay_v1.py`; legacy `delayMilestonesView` | React preserves the `end_date` shift and adds dependency propagation; browser validation pending |
| **Validate selected milestones together** (set done/quotity) | Individual React milestone editing | **Intentionally dropped** | Legacy `validateMilestonesView` remains for legacy callers; React form edits status/progress | Individual React validation/editing is sufficient; no bulk action migrated |
| Gantt/temporal planning | Planning list/Gantt switch and `PlanningGanttView` | Replaced differently | `frontend/src/pages/ProjectPlanningPanel.tsx` | keep React view structure |
| Project Leave list/calendar and leave creation | Calendar/list/resources and shared Leave Sheet | Implemented | `frontend/src/pages/ProjectCalendarPanel.tsx` | keep React behavior |
| Funds, consolidated totals, Fund items and expense timepoints | `ProjectFundingPanel` and selected Fund detail | Implemented | `frontend/src/pages/ProjectFundingPanel.tsx` | keep React behavior |
| Fund expenses and related actions | Shared `ExpenseSection` under selected Fund | Implemented | `frontend/src/pages/ProjectFundingPanel.tsx`, `ExpenseSection.tsx` | keep React behavior |
| Budget and Contribution CRUD | Independent React Budget and Contribution sections | Implemented | `frontend/src/pages/ProjectBudgetsPanel.tsx` | keep React behavior |
| Contracts and associated expenses | Project `ContractSection` and expense detail workflow | Implemented | `frontend/src/pages/ProjectDetailPage.tsx`, `ContractSection.tsx` | keep React behavior |
| Project-specific financial graphs under legacy “Dashboard” | Configurable Project Dashboard route | Replaced differently | Legacy `#project_recette_graph`/`#project_expense_graph`; React `/projects/:id/dashboard` | No legacy graph parity required; any redesign is a **React-only follow-up**, outside Phase 2 blocker |
| Report template selection, Word/PDF actions | Header action menu and validated `ReportExportDialog` | Replaced differently | `frontend/src/pages/ProjectDetailPage.tsx`, `ReportExportDialog.tsx` | keep React UI |
| Report rendering and file download | Shared Django report engine through API/legacy URLs | Backend-only | `backend/reports/views.py`, `frontend/src/api/reports.ts` | retain Django backend routes |
| Admin deep link, Project settings, favorites/subscription | Entity action menu, `SettingsSheet`, `ObjectPreferenceActions` | Implemented | `frontend/src/pages/ProjectDetailPage.tsx` | keep React behavior |
| Empty legacy calendar-filter placeholder | Actual React plugin filters | Legacy artifact | `#calendar-project-filter` comment in `project_single.html`; `ProjectCalendarPanel.tsx` | no placeholder migration |
| Historical `/project/print/` HTML route | React calendar print; Gantt also prints in React | Needs runtime check | `backend/project/urls.py`, `ProjectCalendarPanel.tsx`, `PlanningGanttView` | retain historical URL pending old-bookmark/print check |

The legacy bulk endpoints remain exposed in Django for legacy callers. React implements bulk delay with dependency propagation and per-item permission checks; bulk validation is intentionally dropped from React. The legacy Project dashboard contains two financial graphs, not a complete dashboard system; React's Project Dashboard is the reference, with any further visual work tracked separately.

### Auth compatibility gap analysis

The new entry points use React UI and Django/allauth business logic. **16 workflows: 9 React + Django backend, 3 Compatibility only, 3 Django intentionally retained, 1 Needs runtime check; 0 confirmed Real gaps.** No auth route should be removed in Phase 2 merely because its normal form now appears in React.

| Auth workflow | React UI | Django/allauth role | Compatibility need | Status | Decision |
| --- | --- | --- | --- | --- | --- |
| Login | `/app/login` form and error feedback | `/api/v1/auth/login/` uses configured allauth form, rate limit and session | Old `/accounts/login/` remains a working legacy entry | React + Django backend | keep backend and legacy entry; no second React login |
| Logout | React user menu | `/api/v1/auth/logout/` clears session | Legacy navbar links to allauth `/accounts/logout/` | React + Django backend | retain legacy logout while shell exists |
| Password change/set for signed-in user | Settings > User account | `/api/v1/settings/account/password/` uses allauth forms/flows | `/accounts/password/change/` and legacy settings links may remain | React + Django backend | keep allauth backend and compatibility page |
| Password-reset request | `/app/password/reset` | `/api/v1/auth/password/reset/` uses allauth form and email; React link requires `REACT_PUBLIC_URL` | Old `/accounts/password/reset/` form can still send a legacy link | React + Django backend | retain both routes and email formats |
| New reset-token bridge | `/app/password/reset/bridge/:key` removes key from URL after exchange | `/api/v1/auth/password/reset/bridge/<key>/` validates token and stores session state | New React emails use it | React + Django backend | keep token/session bridge |
| New reset confirmation | `/app/password/reset/:uid` handles invalid/saved states | `/api/v1/auth/password/reset/<uid>/` validates and saves with configured allauth form | None beyond session bridge | React + Django backend | keep backend validation |
| Email-address management | Settings > User account: add, remove, primary, resend | `/api/v1/settings/account/emails/` uses allauth `EmailAddress` and flows | Old `/accounts/email/` remains usable in legacy | React + Django backend | retain backend/legacy page while old links exist |
| Email confirmation from message | New messages open `/app/email/confirm/bridge/:key`, then a React confirmation page without the key in its URL | API bridge checks the allauth key in the session; explicit POST delegates confirmation to allauth, with confirmation-on-GET disabled | New messages use `REACT_PUBLIC_URL`; old `/accounts/confirm-email/...` links remain valid | React + Django backend | retain the legacy callback and templates for previously sent links |
| New invitation link | `/app/invitations/accept/:token` shows accepted/expired/invalid/account-exists states | `/api/v1/auth/invitations/bridge/` validates and stores key in session | New emails point to React through adapter | React + Django backend | keep bridge and token safeguards |
| Invitation signup | `/app/invitations/accept/` shows configured form fields/errors | `/api/v1/auth/invitations/current/` uses allauth signup and django-invitations acceptance; provisioning is server-side | Old signup hand-off is separate | React + Django backend | keep Django signup logic, React form |
| Previously sent invitation link | Existing `/invitations/accept/<key>/` opens django-invitations flow | Included invitation URLs and explicit `AcceptInvite` route in `backend/labsmanager/urls.py` | Old emails may still contain it | Compatibility only | retain; check actual URL resolution/order and old-link outcome at runtime |
| Previously sent reset link | Allauth reset-key URL can show legacy form | Allauth validates old token directly; React bridge applies only to new React-requested emails | Old emails may still contain it | Compatibility only | retain old token URL and templates |
| Old allauth login/logout/change/email and signup links | Normal path is React; old forms remain Django | `/accounts/` include and `/accounts/signup/` explicit invitation-aware view | Legacy navbar/templates and bookmarks | Compatibility only | do not redirect blindly; POST/callback behavior must survive |
| Inactive account | No dedicated React page identified | `account/account_inactive.html` gives the allauth inactive-account state | Can be reached through exceptional allauth flow | Django intentionally retained | acceptable fallback; assess polish only if observed |
| Email-confirmation invalid/expired and related allauth error screens | React shows invalid/expired and already-confirmed states for new links | `account/email_confirm.html` still handles old links; allauth owns confirmation | Previously sent links and exceptional allauth paths still need Django | React + Django compatibility | retain legacy template and callback |
| Non-invitation/open-signup edge case | No general React signup route | Adapter allows signup only with verified invitation session or `ACCOUNT_ALLOW_SINGUP`; legacy `/accounts/signup/` exists | Deployment configuration determines reachability | Needs runtime check | check target configuration and desired entry path before treating as a gap |

Evidence: `frontend/src/pages/LoginPage.tsx`, `PasswordResetPage.tsx`, `InvitationAcceptPage.tsx`, `SettingsHubPage.tsx`; `frontend/src/router/AppRouter.tsx`; `backend/labsmanager/api_v1.py`, `invitation_api_v1.py`, `labs_account_adaptater.py`, `urls.py`; `backend/settings/account_api_v1.py`; `backend/templates/account/`. The old invitation URL appears both under the included `invitations.urls` and as an explicit route; test which view resolves it before any redirect. The React reset token bridge is for new reset emails initiated through React; the adapter otherwise returns allauth's URL. Old email links cannot be inferred safe to remove from current templates.

## 4. Django routes intentionally retained

| Route/family | Role and consumer | Reason to keep |
| --- | --- | --- |
| `/admin/` and protected admin deep links | Django Admin, staff/superusers and React admin links | Administrative UI; **Keep Django**, outside React migration debt. |
| `/api/`, `/api/v1/`, `/api/settings/`, `/api/plugin/`, `/api-auth/` | React, legacy JS, plugins and DRF auth | Backend contracts, including mutations and permission checks. Audit callers before retiring any older API. |
| `/reports/employee|project/.../<template>/`, PDF variants, `/reports/download_template/...` | Legacy reports and downloads | File generation uses the Django report engine; React `/api/v1/reports/...` also invokes it. Keep export/download semantics, assess only obsolete selection modals. |
| `/calendar/print`, `/project/print/` | Legacy print workflows | Server print routes; verify users/bookmarks before replacement. React print is a distinct workflow. |
| `/import/get_template/` | Legacy import template download | Download endpoint; keep while legacy import exists, compare with React API before change. |
| `/accounts/`, `/invitations/`, `/invitations/accept/<key>/`, `/accounts/signup/` | Allauth, django-invitations, React bridges and old emailed links | Token verification, callbacks and backward compatibility; do not remove because React has forms. |
| `/report/<path:path>`, static and media serving rules | Authorized report file delivery | Security-sensitive backend delivery, not a UI page. |
| `/jsreverse.json`, `/faicon/`, `/common/*`, `/notification/*` | Legacy JS, icons, preferences, notification actions | Technical/fragment endpoints. Some are still used by legacy pages. |
| `/staff/ajax/*`, `/project/ajax/*`, `/fund/ajax/*`, `/expense/ajax/*`, `/infos/notes/*`, `/settings/setting_*`, `/dashboard/*/card` | Legacy list/detail JS and partial templates | Retain with their parent pages; a missing link in React does not prove these unused. |
| Dynamic `/plugin/` and `/api/plugin/` | Enabled plugin `urls` mixins and plugin API | Plugin-owned contract; inspect each deployed plugin before any route change. |

`backend/reports/views.py` shows the distinction between modal template choosers and document rendering. `backend/templates/dashboard/global_dashboard.html` loads `/dashboard/*/card` fragments. `backend/data/static/js/import_base.js` calls the legacy import/confirm/template paths. `backend/templates/project/project_single.html`, `employee/employee_single.html`, `team/team_single.html` and `organization/institution_single.html` load notes/fragments dynamically.

## 5. Compatibility and redirect candidates

No redirect is implemented here. Parameterized routes must preserve IDs, resource type, query state where meaningful, permissions and old email/bookmark behavior.

| Legacy route | Proposed React target | Parameters to preserve | Known external callers | Risk | Readiness |
| --- | --- | --- | --- | --- | --- |
| `/`, `/index/` | `/app/` | login/next destination | Bookmarks likely; root proxy already redirects in R4.2 | Low | Validate deployment/auth behavior |
| `/staff/employee/`, `/staff/team/`, `/project/`, `/expense/`, `/dashboard/` | `/app/employees/`, `/app/teams/`, `/app/projects/`, `/app/tools/contracts`, `/app/dashboard` | List filters if carried in query string | Legacy navbar; bookmarks unknown | Medium | Redirect mapping and old-link check |
| `/staff/employee/<pk>` | `/app/employees/<pk>` | Employee PK, optional tab intent | Email fallback and `global_report.html` | High | Accepted React detail; preserve old URL as redirect |
| `/staff/team/<pk>` | `/app/teams/<pk>` | Team PK, tab intent | Email fallback | Medium | Preserve old URL as redirect |
| `/project/<pk>` | `/app/projects/<pk>` | Project PK, tab intent | Email fallback, old bookmarks | High | Preserve old URL as redirect |
| `/calendar/main`, `/settings/` | `/app/calendars`, `/app/settings/user` or contextual section | Calendar scope; settings anchor | Email fallback to calendar/notifications | High | Update email helper and old-link handling together |
| `/staff/organisation_chart/`, `/import/` | `/app/tools/organization-chart`, `/app/tools/import` | Import profile/query if used | Legacy tools navigation | Medium | Validate workflows first |
| `/infos/<app>/<model>/<pk>` | Institution **or** Funder React detail | app/model/PK determine entity; never collapse IDs | Legacy tables, preference links | High | Explicit model map required |
| `/infos/` | Institution/Funder choice or scoped list | Intended type | Legacy navbar | Medium | No single equivalent target |
| `/fund/finder` | Specialized Fund items, Budget finder or Contract tool | Filter and result type | Legacy tools card | Medium | Functional replacement accepted; choose navigation/redirect manually, not a unified finder |

`backend/labsmanager/email_urls.py` actively chooses React destinations only when `REACT_PUBLIC_URL` is configured; otherwise it uses Django routes. `backend/templates/email/global_report.html` still links directly to `employee`. Old messages remain in recipients' inboxes even if current templates change.

## 6. Candidate removals for Phase 2

**None confirmed.** The legacy shell currently calls main pages and their modal/fragment endpoints, while external/bookmark usage is not observable statically. The three unreferenced dashboard placeholder pages are *investigation* candidates, not proven removals. Report selection modals, legacy charts and the old import screens become candidates only after their parent UI is retired and their incoming links, downloads and permissions are checked. Record any verified removal in `STATUS.md` or the project's release history and remove the retired route from this active matrix.

## 7. Templates potentially orphaned

| Template | Evidence / former role | Confidence | Next check |
| --- | --- | --- | --- |
| `backend/templates/staff/employee_add.html` | No render/include reference found outside locale catalogs in targeted code search; older Employee form candidate. | Medium | Check runtime render and template inheritance before removal. |
| `backend/templates/dashboard/dasboard_simple.html` | No view/include reference found; spelling preserved as stored. | Medium | Check dynamic template names and deployment logs. |
| `backend/templates/employee/organisation_chart.html` | Rendered by a function in `backend/staff/views.py`, but that function has no matching route in inspected `staff/urls.py`. | Low | Check direct callers and distinguish from the active `employee/organization_chart.html`. |

Not orphaned: `backend/templates/email/global_report.html` is rendered by `backend/labsmanager/tasks.py`; `backend/templates/import/import_out.html` is used by `backend/import/mixin.py`; `backend/templates/project/active.html` is included by another Project template. Allauth templates can be selected dynamically by the framework, so lack of a literal render call is not removal evidence. Dedicated legacy JS/CSS should be inventoried **per retired page** later, not deleted now.

## 8. Plugin-specific legacy dependencies

`backend/plugin/urls.py` assembles `/plugin/` routes from enabled plugins with a `urls` mixin; `backend/plugin/registry.py` can refresh the mounted patterns. The legacy Settings page renders plugin metadata, settings, scheduled tasks, URLs and optional `get_settings_content(request)` HTML through `settings/plugin.html` and `backend/plugin/templatetags/plugin_tags.py`. React Admin Plugin Detail renders structured settings, schedule and URLs; it does not render arbitrary plugin-provided HTML. Notification email templates also retain plugin `mailsubscription` inclusions. These are real extension points, not generic obsolete templates. The available sample and the externally deployed KioskDashboard do not establish all production plugin routes or custom settings content. Inventory the enabled plugins and their menu links in the target deployment before Phase 2 routing changes; do not alter the registry as part of this audit.

## 9. Unknown / runtime validation required

| Route/workflow | Why static code is insufficient | Validation |
| --- | --- | --- |
| Project bulk milestone actions | React delay is implemented with dependency propagation; React bulk validation is intentionally dropped. | Verify delay in the browser and retain legacy routes until caller audit. |
| Main legacy entry paths, reports and bookmarks | Main React journeys are accepted, but old URLs, query parameters and historical document links remain in circulation. | Test redirect mapping, old emailed links and anonymized access logs; do not repeat general React browser validation. |
| `/fund/finder` | Functional replacement by specialized tools is accepted; there is no single React URL for old bookmarks. | Choose a navigation/redirect destination as a separate UI task. |
| `/infos/institution/<pk>` | Registered view appears to require missing `app/model`; no caller found. | Request it in a safe test environment and inspect access logs/bookmarks. |
| `/dashboard/fundloss`, `/fundstale`, `/contractstale` | Placeholder views lack internal callers, but external use is unknown; their `/card` siblings are active. | Logs and browser check before proposing removal. |
| Plugin URLs/custom settings | Routes and HTML depend on deployed plugin configuration, including external packages. | Enumerate active plugins, `urls` mixins, `get_settings_content` and links in the deployment. |
| Auth/invitations/reset and email URLs | Tokens and old messages outlive current frontend code; allauth confirmation and inactive-account screens remain visible by design. | Test old invitation/reset links, confirmation callbacks, unusual signup configuration and host/proxy behavior. |
| Potential orphan templates | Dynamic template resolution or older deployments may still refer to them. | Targeted runtime/log check, then separate removal review. |

## 10. Recommended next migration lots

| Priority | Lot | Functional value | Main dependencies | Risk | Estimated effort |
| --- | --- | --- | --- | --- | --- |
| 1 | Validate Project Planning bulk delay in the browser | Confirms the new DAG-aware React workflow | Project Planning API and existing dependency graph | Low | Medium |
| 2 | Plugin route and custom-settings inventory | Identifies deployment-specific plugin UI and extension dependencies | Enabled plugins, Settings HTML and React plugin detail | High | Small |
| 3 | Compatibility map for old detail/email/auth URLs | Keeps bookmarks and messages working when React becomes sole UI | `email_urls.py`, allauth/invitations, model-aware Organization mapping | High | Medium |
| 4 | Redirect accepted top-level legacy pages | Removes duplicate navigation without removing backend workflows | Old-link checks, logs, redirect tests, proxy rules | Medium | Medium |
| 5 | Retire unused modal/fragment/static bundles in small families | Reduces legacy code after parent pages stop calling it | Per-page JS/CSS and endpoint caller audit | High | Large |

## 11. Phase 2 cleanup checklist

Apply this checklist **per route/workflow**, not once for the whole application:

- [ ] React read/write/permission parity complete for the same object and scope.
- [ ] Browser validation complete for relevant roles, languages and legacy edge cases.
- [ ] No active template, JavaScript, React, API or worker caller remains.
- [ ] No enabled plugin route, setting or email inclusion depends on it.
- [ ] No old email, auth callback, external integration or bookmark needs the original response.
- [ ] Redirect target and parameter/model mapping decided; compatibility period agreed.
- [ ] Report, export, download, print and import backend routes preserved where required.
- [ ] Dedicated legacy JS/CSS and template dependencies identified.
- [ ] Replacement and redirect tests exist where behavior changes.
- [ ] `LEGACY_AUDIT.md` and status/release documentation updated.
- [ ] Removal approved after deployment-specific evidence review.

After a migration, update the row's React equivalent, parity, classification and Phase 2 action. After a redirect, classify the retained URL as compatibility. After removal, delete the route from the active matrix and briefly record the change in `STATUS.md` or the release history; do not grow an exhaustive history here.
