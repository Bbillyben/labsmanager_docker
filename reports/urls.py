from django.urls import include, path, re_path
from . import views

urlpatterns = [
    path('employee/<pk>/<int:template>/', views.userReport, name='employee_report'),
    path('employee/<pk>/generate/', views.EmployeeReportView.as_view(), name="employee_report_generate"),
    path('project/<pk>/<int:template>/', views.projectReport, name='project_report'),
    path('project/<pk>/generate/', views.ProjectReportView.as_view(), name="project_report_generate"),
]