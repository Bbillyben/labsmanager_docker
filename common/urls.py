from django.urls import include, path, re_path
from . import views, views_modal, tasks


urlpatterns = [
    path('nav/', views.get_nav_favorites, name='nav_favorites'),
    path('nav/accordion', views.get_nav_favorites_accordion, name='nav_favorites_accordion'),
    path('fav-toggle/', views.toggle_favorites, name='favorite_toggle'), 
    path('fav-star/', views.get_user_fav_obj, name='favorite_star'), 
    
    path('sub-bell/', views.get_user_subscription_obj, name='subscription_bell'), 
    path('sub-toggle/', views.toggle_subscription, name='subscription_toggle'), 
    path('help_btn/', views.get_help_btn, name='help_btn'), 
    
    path('subscription/<pk>/delete', views_modal.SubscriptionDeleteView.as_view(), name='delete_subscription'),
    path('favorite/<pk>/delete', views_modal.FavoriteDeleteView.as_view(), name='delete_favorite'),
    
    path('subscription/send_test_mail', tasks.send_test_mail, name='subs_test_mail'),
    path('subscription/send_test', tasks.test_check, name='subs_check_tasks'),
    path('subscription/open_test', views.get_test_email, name='get_test_mail'),
    
    path('user_maillist/', views.get_user_emaillist, name='user_emaillist'),
    
    path('changepassword/', views_modal.ChangePasswordBSView.as_view(), name='change_password_modal'),
    
]