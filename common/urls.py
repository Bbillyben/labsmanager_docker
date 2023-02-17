from django.urls import include, path, re_path
from . import views


urlpatterns = [
    path('nav/', views.get_nav_favorites, name='nav_favorites'),
    path('fav-toggle/', views.toggle_favorites, name='favorite_toggle'), 
    path('fav-star/', views.get_user_fav_obj, name='favorite_star'), 
]