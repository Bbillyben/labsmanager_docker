from django.urls import include, path, re_path
from .views import launch_check_notification, send_all_pending_notification

urlpatterns = [
    path('check', launch_check_notification, name='launch_notif'),
    path('send_pending', send_all_pending_notification, name='launch_send_pending'),
]