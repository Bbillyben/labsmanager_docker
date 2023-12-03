from django.urls import include, path, re_path
from .ajax import ajax_staff
from . import views, views_modal

urlpatterns = [
    path('employee/', views.EmployeeIndexView.as_view(), name='employee_index'),
    path('', views.EmployeeIndexView.as_view(), name='staff'),
    path('employee/<int:pk>', views.EmployeeView.as_view(), name='employee'),
    path('team/', views.TeamIndexView.as_view(), name='team_index'),
    path('team/<int:pk>', views.TeamView.as_view(), name='team_single'),
    path('organisation_chart/',views.OrganisationChartView.as_view(), name="organisation_chart_index")
]

#  for ajax
urlpatterns += [
    re_path(r'[a-z]ajax/{0,1}', ajax_staff, name='ajax_staff'),
    path('team/<pk>/resume', views.get_team_resume, name='team_resume_table'),  # template for user valid check box
    path('team/<pk>/mate', views.get_team_mate, name='team_mate_table'),  # template for user valid check box
]

# for modal

urlpatterns += [
    path('employee/add/', views.EmployeeCreateView.as_view(), name='create_employee'),  # modal creation employee
    path('employee/<pk>/udpate', views.EmployeeUpdateView.as_view(), name='update_employee'),  # modal update employee
    path('employee/<pk>/delete', views.EmployeeRemoveView.as_view(), name='delete_employee'),  # modal delete employee
    path('employee/<employee>/status/add/', views.EmployeeStatusCreateView.as_view(), name='create_status_employee'),    
    
    path('employee/<pk>/udpate_user', views_modal.EmployeeUserUpdateView.as_view(), name='update_employee_user'),  # modal update employee's user
    path('user/<pk>/udpate_emp', views_modal.UserEmployeeUpdateView.as_view(), name='update_user_employee'),  # modal update employee'user from admin
    
    # for status
    path('status/<pk>/update/', views.StatusUpdateView.as_view(), name='update_status_employee'),  # specific for status view
    path('status/<pk>/delete/', views.StatusDeleteView.as_view(), name='delete_status_employee'),  # specific for status view
    # for Superior
    path('employee/<employee>/superior/add/', views_modal.EmployeeSuperiorCreateView.as_view(), name='create_superior'),  # modal creation Team
    path('superior/<pk>/udpate', views_modal.EmployeeSuperiorUpdateView.as_view(), name='update_superior'),  # modal update Team
    path('superior/<pk>/delete', views_modal.EmployeeSuperiorDeleteView.as_view(), name='delete_superior'),  # modal delete Team
    
    
    # for info
    path('employee/<employee>/info/add/', views.EmployeeInfoCreateView.as_view(), name='create_info_employee'),
    path('info/<pk>/update/', views.EmployeeInfoUpdateView.as_view(), name='update_info_employee'),  # specific for status view
     path('info/<pk>/delete/', views.EmployeeInfoDeleteView.as_view(), name='delete_info_employee'), 
    # for sub template 
    path('ajax/<pk>/activ', views.get_employee_valid, name='user_valid_temp'),  # template for user valid check box
    path('ajax/<pk>/info', views.get_employee_info_table, name='employee_info_table'), 
    # for team
    path('team/add/', views_modal.TeamCreateView.as_view(), name='create_team'),  # modal creation Team
    path('team/<pk>/udpate', views_modal.TeamUpdateView.as_view(), name='update_team'),  # modal update Team
    path('team/<pk>/delete', views_modal.TeamRemoveView.as_view(), name='delete_team'),  # modal delete Team
    
    # for teamMate
    path('teammate/add/', views_modal.TeamMateCreateView.as_view(), name='create_teammate'), 
    path('teammate/<pk>/delete', views_modal.TeamMateRemoveView.as_view(), name='delete_teammate'), 
    path('teammate/<pk>/update', views_modal.TeamMateUpdateView.as_view(), name='update_teammate'),
    
    path('employeetype/add/', views_modal.EmployeeTypeCreateView.as_view(), name='add_employeetype'),
    path('employeetype/<pk>/update/', views_modal.EmployeeTypeUpdateView.as_view(), name='update_employeetype'),
    
    path('genericinfotype/add/', views_modal.GenericInfoTypeCreateView.as_view(), name='add_genericinfotype'),
    path('genericinfotype/<pk>/update/', views_modal.GenericInfoTypeUpdateView.as_view(), name='update_genericinfotype'),  
    
    
]