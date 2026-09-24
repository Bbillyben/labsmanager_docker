from django.urls import path
from endpoints.api_v1 import (
    EditableProjectCandidatesV1View,
    ProjectPlanningItemsV1View,
    MilestoneDependenciesV1View,
    MilestoneDependencyDetailV1View,
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
    EmployeeMilestoneV1View,
    EmployeeProjectParticipationV1View,
    EmployeeProjectWorkloadV1View,
    EmployeeStatusHistoryV1View,
)

from .api_v1 import CurrentUserView, LoginV1View, LogoutV1View
from project.api_v1 import ProjectCapabilitiesV1View, ProjectDetailV1View, ProjectFilterOptionsV1View, ProjectListV1View


app_name = "api_v1"

urlpatterns = [
    path("projects/", ProjectListV1View.as_view(), name="projects"),
    path("projects/capabilities/", ProjectCapabilitiesV1View.as_view(), name="project-capabilities"),
    path("projects/filter-options/", ProjectFilterOptionsV1View.as_view(), name="project-filter-options"),
    path("projects/<int:pk>/", ProjectDetailV1View.as_view(), name="project-detail"),
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
        EmployeeContractListV1View.as_view(),
        name="employee-contracts",
    ),
    path(
        "employees/<int:pk>/contracts/<int:contract_pk>/",
        EmployeeContractDetailV1View.as_view(),
        name="employee-contract-detail",
    ),
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
