from django.urls import include, path, re_path
from . import views

urlpatterns = [
    path('employee/<pk>/<int:template>/', views.userReport, name='employee_report'),
    path('employee/<pk>/generate/', views.EmployeeReportView.as_view(), name="employee_report_generate")
]