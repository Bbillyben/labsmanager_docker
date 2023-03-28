from django.urls import include, path, re_path
from . import views_modal, views
from .ajax import ajax_project

urlpatterns = [
    path('', views.ProjectIndexView.as_view(), name='project_index'),
    path('<pk>', views.ProjectView.as_view(), name='project_single'),
    path('<pk>/fundoverview/', views.get_project_fund_overview, name='project_fund_overview'),
    
    
    # for sub template 
    path('ajax/<pk>/resume', views.get_project_resume, name='user_valid_temp'),  # template for user valid check box
]

#  for ajax
urlpatterns += [
    re_path(r'[a-z]ajax/', ajax_project, name='ajax_project'),
]

# for modal

urlpatterns += [
    path('ajax/add/', views_modal.ProjectCreateView.as_view(), name='create_project'), 
    path('ajax/<pk>/udpate',views_modal.ProjectUpdateView.as_view(), name='update_project'),  
    path('ajax/<pk>/delete', views_modal.ProjectRemoveView.as_view(), name='delete_project'),  
    
    path('ajax/<pk>/participant/add', views_modal.ParticipantCreateView.as_view(), name='add_participant'),
    path('ajax/participant/add/<employee>', views_modal.ParticipantCreateView.as_view(), name='add_participant_open'),  
    
    path('ajax/participant/<pk>/udpate', views_modal.ParticipantUpdateView.as_view(), name='update_participant'),  
    path('ajax/participant/<pk>/delete', views_modal.ParticipantDeleteView.as_view(), name='delete_participant'),  
    
    path('ajax/<pk>/institution/add', views_modal.InstitutionCreateView.as_view(), name='add_institution'),
    
    path('institution/add', views_modal.InstitutionDirectCreateView.as_view(), name='add_institution_direct'),
    path('institution/<pk>/update/', views_modal.InstitutionUpdateView.as_view(), name='update_institution_direct'),

]