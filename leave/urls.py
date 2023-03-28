from django.urls import include, path, re_path

from . import views, views_modal


urlpatterns = [
    path('main', views.main_calendar_view, name='calendar_main'),  
]

# for modal

urlpatterns += [
    path('add/', views_modal.LeaveItemCreateView.as_view(), name='add_leave'), 
    path('update/<pk>/', views_modal.LeaveItemUpdateView.as_view(), name='update_leave'),  
    path('delete/<pk>/', views_modal.LeaveItemDeleteView.as_view(), name='update_leave'),
    path('add/employee/<emp_pk>/', views_modal.LeaveItemCreateView.as_view(), name='add_leave_emp'),
    path('leave_type/add/', views_modal.LeaveTypeCreateView.as_view(), name='add_leave_type'),
    path('leave_type/<pk>/update/', views_modal.LeaveTypeUpdateView.as_view(), name='update_leave_type'),
]