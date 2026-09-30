from django.urls import path
from endpoints.api_v1 import (
    EditableProjectCandidatesV1View,
    ProjectPlanningItemsV1View,
    MilestoneDependenciesV1View,
    MilestoneDependencyDetailV1View,
    ProjectPlanningV1View,
    ProjectPlanningItemV1View,
)

from staff.api_v1 import (
    EmployeeBudgetListV1View,
    EmployeeDetailV1View,
    EmployeeContractDetailV1View,
    EmployeeContractListV1View,
    EmployeeContributionListV1View,
    EmployeeContributionWorkloadV1View,
    EmployeeGenericInfoV1View,
    EmployeeGenericInfoDetailV1View,
    GenericInfoTypeV1View,
    EmployeeHierarchyV1View,
    EmployeeLeaveListV1View,
    EmployeeLeaveCapabilitiesV1View,
    EmployeeLeaveDetailV1View,
    LeaveTypeCatalogueV1View,
    EmployeeCalendarV1View,
    EmployeeCalendarFilterV1View,
    EmployeeListV1View,
    EmployeeListExportV1View,
    EmployeeListFilterOptionsV1View,
    EmployeeMilestoneV1View,
    EmployeeMilestoneDetailV1View,
    EmployeeProjectParticipationV1View,
    EmployeeProjectWorkloadV1View,
    EmployeeStatusHistoryV1View,
)

from .api_v1 import CurrentUserView, LoginV1View, LogoutV1View
from project.api_v1 import ProjectCapabilitiesV1View, ProjectDetailV1View, ProjectFilterOptionsV1View, ProjectListV1View, ProjectListExportV1View, ProjectOverviewOptionsV1View, project_child_view
from project.calendar_api_v1 import ProjectCalendarV1View, ProjectCalendarFiltersV1View, ProjectCalendarParticipantsV1View, ProjectCalendarLeaveCreateV1View, ProjectCalendarLeaveDetailV1View
from fund.api_v1 import ProjectFundingView, FundingOptionsView, FundingFundView, FundItemView, ExpensePointView
from fund.budget_api_v1 import (
    ProjectBudgetCollection, ProjectBudgetDetail, ProjectBudgetOptions,
    ProjectContributionCollection, ProjectContributionDetail, ProjectContributionOptions,
)
from expense.api_v1 import ExpenseCollectionV1View, ExpenseDetailV1View, ExpenseOptionsV1View, ExpenseSyncV1View
from expense.contracts_api_v1 import (
    ContractCollectionV1View, ContractDetailV1View, ContractOptionsV1View,
    ContractEmployeeEndDateSyncV1View, EmployeeContractCapabilitiesV1View,
)
from reports.api_v1 import ReportExportV1View
from settings.api_v1 import ProjectSettingsV1View, ProjectSettingDetailV1View
from infos.api_v1 import GenericNotesCollectionV1View, GenericNoteDetailV1View


app_name = "api_v1"

urlpatterns = [
    path("notes/<str:scope>/<int:pk>/", GenericNotesCollectionV1View.as_view(), name="generic-notes"),
    path("notes/<str:scope>/<int:pk>/<int:note_id>/", GenericNoteDetailV1View.as_view(), name="generic-note-detail"),
    path("projects/<int:project_id>/calendar/", ProjectCalendarV1View.as_view(), name="project-calendar"),
    path("projects/<int:project_id>/calendar/filters/", ProjectCalendarFiltersV1View.as_view(), name="project-calendar-filters"),
    path("projects/<int:project_id>/calendar/participants/", ProjectCalendarParticipantsV1View.as_view(), name="project-calendar-participants"),
    path("projects/<int:project_id>/calendar/leaves/", ProjectCalendarLeaveCreateV1View.as_view(), name="project-calendar-leave-create"),
    path("projects/<int:project_id>/calendar/leaves/<int:leave_id>/", ProjectCalendarLeaveDetailV1View.as_view(), name="project-calendar-leave-detail"),
    path("projects/<int:project_id>/contracts/", ContractCollectionV1View.as_view(), name="project-contracts"),
    path("projects/<int:project_id>/contracts/options/", ContractOptionsV1View.as_view(), name="project-contract-options"),
    path("projects/<int:project_id>/contracts/<int:contract_id>/", ContractDetailV1View.as_view(), name="project-contract-detail"),
    path("projects/<int:project_id>/contracts/<int:contract_id>/sync-employee-end-date/", ContractEmployeeEndDateSyncV1View.as_view(), name="project-contract-sync-employee-end-date"),
    path("projects/<int:pk>/contracts/<int:contract_id>/expenses/", ExpenseCollectionV1View.as_view(), name="project-contract-expenses"),
    path("projects/<int:pk>/contracts/<int:contract_id>/expenses/options/", ExpenseOptionsV1View.as_view(), name="project-contract-expense-options"),
    path("projects/<int:pk>/contracts/<int:contract_id>/expenses/<int:expense_id>/", ExpenseDetailV1View.as_view(), name="project-contract-expense-detail"),
    path("employees/<int:employee_id>/contracts/capabilities/", EmployeeContractCapabilitiesV1View.as_view(), name="employee-contract-capabilities"),
    path("employees/<int:employee_id>/contracts/options/", ContractOptionsV1View.as_view(), name="employee-contract-options"),
    path("reports/<str:entity>/<int:pk>/<str:format_name>/", ReportExportV1View.as_view(), name="report-export"),
    path("projects/<int:pk>/settings/", ProjectSettingsV1View.as_view(), name="project-settings"),
    path("projects/<int:pk>/settings/<str:key>/", ProjectSettingDetailV1View.as_view(), name="project-setting-detail"),
    path("projects/<int:pk>/budgets/", ProjectBudgetCollection.as_view(), name="project-budgets"),
    path("projects/<int:pk>/budgets/options/", ProjectBudgetOptions.as_view(), name="project-budget-options"),
    path("projects/<int:pk>/budgets/<int:item_id>/", ProjectBudgetDetail.as_view(), name="project-budget-detail"),
    path("projects/<int:pk>/budgets/<int:budget_id>/expenses/", ExpenseCollectionV1View.as_view(), name="project-budget-expenses"),
    path("projects/<int:pk>/budgets/<int:budget_id>/expenses/options/", ExpenseOptionsV1View.as_view(), name="project-budget-expense-options"),
    path("projects/<int:pk>/budgets/<int:budget_id>/expenses/<int:expense_id>/", ExpenseDetailV1View.as_view(), name="project-budget-expense-detail"),
    path("projects/<int:pk>/contributions/", ProjectContributionCollection.as_view(), name="project-contributions"),
    path("projects/<int:pk>/contributions/options/", ProjectContributionOptions.as_view(), name="project-contribution-options"),
    path("projects/<int:pk>/contributions/<int:item_id>/", ProjectContributionDetail.as_view(), name="project-contribution-detail"),
    path("funds/<int:fund_id>/expenses/", ExpenseCollectionV1View.as_view(), name="fund-expenses"),
    path("funds/<int:fund_id>/expenses/options/", ExpenseOptionsV1View.as_view(), name="fund-expense-options"),
    path("funds/<int:fund_id>/expenses/sync/", ExpenseSyncV1View.as_view(), name="fund-expense-sync"),
    path("funds/<int:fund_id>/expenses/<int:expense_id>/", ExpenseDetailV1View.as_view(), name="fund-expense-detail"),
    path("employees/<int:employee_id>/contracts/<int:contract_id>/expenses/", ExpenseCollectionV1View.as_view(), name="contract-expenses"),
    path("employees/<int:employee_id>/contracts/<int:contract_id>/expenses/options/", ExpenseOptionsV1View.as_view(), name="contract-expense-options"),
    path("employees/<int:employee_id>/contracts/<int:contract_id>/expenses/<int:expense_id>/", ExpenseDetailV1View.as_view(), name="contract-expense-detail"),
    path("projects/", ProjectListV1View.as_view(), name="projects"),
    path("projects/export/", ProjectListExportV1View.as_view(), name="project-list-export"),
    path("projects/capabilities/", ProjectCapabilitiesV1View.as_view(), name="project-capabilities"),
    path("projects/filter-options/", ProjectFilterOptionsV1View.as_view(), name="project-filter-options"),
    path("projects/<int:pk>/", ProjectDetailV1View.as_view(), name="project-detail"),
    path("projects/<int:pk>/overview-options/", ProjectOverviewOptionsV1View.as_view(), name="project-overview-options"),
    path("projects/<int:pk>/generic-info/", project_child_view("generic-info"), name="project-generic-info"),
    path("projects/<int:pk>/generic-info/<int:item_id>/", project_child_view("generic-info", detail=True), name="project-generic-info-detail"),
    path("projects/<int:pk>/institutions/", project_child_view("institutions"), name="project-institutions"),
    path("projects/<int:pk>/institutions/<int:item_id>/", project_child_view("institutions", detail=True), name="project-institution-detail"),
    path("projects/<int:pk>/participants/", project_child_view("participants"), name="project-participants"),
    path("projects/<int:pk>/participants/<int:item_id>/", project_child_view("participants", detail=True), name="project-participant-detail"),
    path("projects/<int:pk>/planning/", ProjectPlanningV1View.as_view(), name="project-planning"),
    path("projects/<int:pk>/planning/<int:item_id>/", ProjectPlanningItemV1View.as_view(), name="project-planning-item"),
    path("projects/<int:pk>/funding/", ProjectFundingView.as_view(), name="project-funding"),
    path("projects/<int:pk>/funding/options/", FundingOptionsView.as_view(), name="project-funding-options"),
    path("projects/<int:pk>/funding/funds/<int:fund_id>/", FundingFundView.as_view(), name="project-funding-fund"),
    path("projects/<int:pk>/funding/funds/<int:fund_id>/items/", FundItemView.as_view(), name="project-funding-items"),
    path("projects/<int:pk>/funding/funds/<int:fund_id>/items/<int:item_id>/", FundItemView.as_view(), name="project-funding-item"),
    path("projects/<int:pk>/funding/funds/<int:fund_id>/expense-points/", ExpensePointView.as_view(), name="project-funding-expense-points"),
    path("projects/<int:pk>/funding/funds/<int:fund_id>/expense-points/<int:item_id>/", ExpensePointView.as_view(), name="project-funding-expense-point"),
    path("leave-types/", LeaveTypeCatalogueV1View.as_view(), name="leave-types"),
    path("planning/projects/", EditableProjectCandidatesV1View.as_view(), name="planning-projects"),
    path("planning/projects/<int:project_id>/items/", ProjectPlanningItemsV1View.as_view(), name="planning-project-items"),
    path("planning/items/<int:successor_id>/dependencies/", MilestoneDependenciesV1View.as_view(), name="planning-dependencies"),
    path("planning/items/<int:successor_id>/dependencies/<int:dependency_id>/", MilestoneDependencyDetailV1View.as_view(), name="planning-dependency-detail"),
    path("generic-info-types/", GenericInfoTypeV1View.as_view(), name="generic-info-types"),
    path(
        "employees/<int:pk>/generic-info/<int:generic_info_id>/",
        EmployeeGenericInfoDetailV1View.as_view(), name="employee-generic-info-detail",
    ),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("auth/login/", LoginV1View.as_view(), name="login"),
    path("auth/logout/", LogoutV1View.as_view(), name="logout"),
    path("employees/", EmployeeListV1View.as_view(), name="employees"),
    path("employees/export/", EmployeeListExportV1View.as_view(), name="employee-list-export"),
    path("employees/filter-options/", EmployeeListFilterOptionsV1View.as_view(), name="employee-filter-options"),
    path(
        "employees/<int:pk>/",
        EmployeeDetailV1View.as_view(),
        name="employee-detail",
    ),
    path(
        "employees/<int:pk>/generic-info/",
        EmployeeGenericInfoV1View.as_view(),
        name="employee-generic-info",
    ),
    path(
        "employees/<int:pk>/contracts/",
        ContractCollectionV1View.as_view(),
        name="employee-contracts",
    ),
    path(
        "employees/<int:pk>/contracts/<int:contract_pk>/",
        ContractDetailV1View.as_view(),
        name="employee-contract-detail",
    ),
    path("employees/<int:pk>/contracts/<int:contract_pk>/sync-employee-end-date/", ContractEmployeeEndDateSyncV1View.as_view(), name="employee-contract-sync-employee-end-date"),
    path(
        "employees/<int:pk>/contributions/",
        EmployeeContributionListV1View.as_view(),
        name="employee-contributions",
    ),
    path(
        "employees/<int:pk>/budgets/",
        EmployeeBudgetListV1View.as_view(),
        name="employee-budgets",
    ),
    path(
        "employees/<int:pk>/leaves/",
        EmployeeLeaveListV1View.as_view(),
        name="employee-leaves",
    ),
    path("employees/<int:pk>/leaves/capabilities/", EmployeeLeaveCapabilitiesV1View.as_view(), name="employee-leave-capabilities"),
    path("employees/<int:pk>/leaves/<int:leave_id>/", EmployeeLeaveDetailV1View.as_view(), name="employee-leave-detail"),
    path(
        "employees/<int:pk>/calendar/",
        EmployeeCalendarV1View.as_view(),
        name="employee-calendar",
    ),
    path(
        "employees/<int:pk>/calendar/filters/",
        EmployeeCalendarFilterV1View.as_view(),
        name="employee-calendar-filters",
    ),
    path(
        "employees/<int:pk>/contribution-workload/",
        EmployeeContributionWorkloadV1View.as_view(),
        name="employee-contribution-workload",
    ),
    path(
        "employees/<int:pk>/milestones/",
        EmployeeMilestoneV1View.as_view(),
        name="employee-milestones",
    ),
    path(
        "employees/<int:pk>/milestones/<int:item_id>/",
        EmployeeMilestoneDetailV1View.as_view(),
        name="employee-milestone-detail",
    ),
    path(
        "employees/<int:pk>/statuses/",
        EmployeeStatusHistoryV1View.as_view(),
        name="employee-statuses",
    ),
    path(
        "employees/<int:pk>/hierarchy/",
        EmployeeHierarchyV1View.as_view(),
        name="employee-hierarchy",
    ),
    path(
        "employees/<int:pk>/project-participations/",
        EmployeeProjectParticipationV1View.as_view(),
        name="employee-project-participations",
    ),
    path(
        "employees/<int:pk>/project-workload/",
        EmployeeProjectWorkloadV1View.as_view(),
        name="employee-project-workload",
    ),
]
