from django.urls import include, path, re_path
from . import views

urlpatterns = [
    path('employee/<pk>/<int:template>/', views.userWordReport, name='employee_report'),
    path('employee/<pk>/generate/', views.EmployeeWordReportView.as_view(), name="employee_report_generate"),
    path('project/<pk>/<int:template>/', views.projectWordReport, name='project_report'),
    path('project/<pk>/generate/', views.ProjectWordReportView.as_view(), name="project_report_generate"),
    
    path('project/pdf/<pk>/<int:template>/', views.projectPDFReport, name='project_pdf_report'),
    path('project/pdf/<pk>/generate/', views.ProjectPDFReportView.as_view(), name="project_pdf_report_generate"),
    
    path('employee/pdf/<pk>/<int:template>/', views.userPDFReport, name='employee_pdf_report'),
    path('employee/pdf/<pk>/generate/', views.EmployeePDFReportView.as_view(), name="employee_pdf_report_generate"),
]