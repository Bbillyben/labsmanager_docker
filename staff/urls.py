from django.urls import include, path, re_path
from .ajax import ajax_staff
from . import views, views_modal

urlpatterns = [
    path('employee/', views.EmployeeIndexView.as_view(), name='employee_index'),
    path('', views.EmployeeIndexView.as_view(), name='staff'),
    path('employee/<int:pk>', views.EmployeeView.as_view(), name='employee'),
    path('team/', views.TeamIndexView.as_view(), name='team_index'),
    path('team/<int:pk>', views.TeamView.as_view(), name='team_single'),
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
    path('status/<pk>/update/', views.StatusUpdateView.as_view(), name='update_status_employee'),  # specific for status view
    path('status/<pk>/delete/', views.StatusDeleteView.as_view(), name='delete_status_employee'),  # specific for status view
    
    # for sub template 
    path('ajax/<pk>/activ', views.get_employee_valid, name='user_valid_temp'),  # template for user valid check box
    
    # for team
    path('team/add/', views_modal.TeamCreateView.as_view(), name='create_team'),  # modal creation Team
    path('team/<pk>/udpate', views_modal.TeamUpdateView.as_view(), name='update_team'),  # modal update Team
    path('team/<pk>/delete', views_modal.TeamRemoveView.as_view(), name='delete_team'),  # modal delete Team
    
    # for teamMate
    path('teammate/add/', views_modal.TeamMateCreateView.as_view(), name='create_teammate'), 
    path('teammate/<pk>/delete', views_modal.TeamMateRemoveView.as_view(), name='delete_teammate'), 
    path('teammate/<pk>/update', views_modal.TeamMateUpdateView.as_view(), name='update_teammate'), 
]