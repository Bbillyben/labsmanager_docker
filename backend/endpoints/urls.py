from django.urls import include, path, re_path
from . import views_modal



urlpatterns = [
    path('add/', views_modal.MilestonesCreateView.as_view(), name='create_milestones'), 
    path('add/<project>', views_modal.MilestonesCreateView.as_view(), name='create_project_milestones'), 
    path('<pk>/update/',views_modal.MilestonesUpdateView.as_view(), name='update_milestones'),  
    path('<pk>/delete/', views_modal.MilestonesDeleteView.as_view(), name='delete_milestones'),  
]


 ### Action form view URL
urlpatterns += [
    path('<project>/delay/',views_modal.delayMilestonesView.as_view(), name='delay_milestones'),  
    path('<project>/validate/',views_modal.validateMilestonesView.as_view(), name='validate_milestones'),  
]