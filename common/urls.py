from django.urls import include, path, re_path
from . import views, views_modal, tasks


urlpatterns = [
    path('nav/', views.get_nav_favorites, name='nav_favorites'),
    path('nav/accordion', views.get_nav_favorites_accordion, name='nav_favorites_accordion'),
    path('fav-toggle/', views.toggle_favorites, name='favorite_toggle'), 
    path('fav-star/', views.get_user_fav_obj, name='favorite_star'), 
    
    path('sub-bell/', views.get_user_subscription_obj, name='subscription_bell'), 
    path('sub-toggle/', views.toggle_subscription, name='subscription_toggle'), 
    
    path('subscription/<pk>/delete', views_modal.SubscriptionDeleteView.as_view(), name='delete_subscription'),
    path('favorite/<pk>/delete', views_modal.FavoriteDeleteView.as_view(), name='delete_favorite'),
    
    path('subscription/send_test', tasks.test_check, name='subs_check_tasks'),
]