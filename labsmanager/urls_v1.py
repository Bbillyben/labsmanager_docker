from django.urls import path

from staff.api_v1 import (
    EmployeeDetailV1View,
    EmployeeHierarchyV1View,
    EmployeeListV1View,
    EmployeeProjectParticipationV1View,
    EmployeeStatusHistoryV1View,
)

from .api_v1 import CurrentUserView, LoginV1View, LogoutV1View


app_name = "api_v1"

urlpatterns = [
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
]
