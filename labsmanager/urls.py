"""labsmanager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from .views import IndexView , redirectIndexView, get_filters_lists, SendTestView
from settings.apiviews import UserSettingsDetail
from rest_framework import routers
from . import apiviews #UserViewSet, GroupViewSet, EmployeeViewSet, ProjectViewSet, FundViewSet
from expense import apiviews as contractApiViews
from project import apiviews as projectApiViews
from fund import apiviews as fundApiViews
from staff import apiviews as staffApiViews
from endpoints import apiviews as endPointApiViews
from leave import apiviews as leaveApiViews
from django.conf.urls.i18n import i18n_patterns
from django_js_reverse import views as jsrev_views


urlpatterns = [
    path('filter_code_list', get_filters_lists, name='filter_code_list'),
    path('admin/', admin.site.urls),
    re_path(r'^index/', IndexView.as_view(), name='index'),
    path('', IndexView.as_view(), name='index'),
    path('staff/', include('staff.urls'), name='staff'),                  # For Staff models
    path('project/', include('project.urls')),              # for project model
    path('fund/', include('fund.urls')),              # for project model
    path('expense/', include('expense.urls')),              # for project model
    path('dashboard/', include('dashboard.urls')),
    path('settings/', include('settings.urls')),
    path('milestones/', include('endpoints.urls')),
    path('calendar/', include('leave.urls')),
]
#  Authentications : 
urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]
#  django_js_reverse
urlpatterns += [
    re_path(r'^jsreverse.json$', jsrev_views.urls_json, name='js_reverse'),
]
    

#  Django Rest Framework

router = routers.DefaultRouter()
router.register(r'users', apiviews.UserViewSet, basename='user')
router.register(r'groups', apiviews.GroupViewSet, basename='groups')
router.register(r'employee', staffApiViews.EmployeeViewSet, basename='employee')
router.register(r'team', staffApiViews.TeamViewSet, basename='team')
router.register(r'project', projectApiViews.ProjectViewSet, basename='project')
router.register(r'fund', fundApiViews.FundViewSet, basename='fund')
router.register(r'funditem', fundApiViews.FundItemViewSet, basename='funditem')
router.register(r'contract', contractApiViews.ContractViewSet, basename='contract')
router.register(r'budget', contractApiViews.BudgetPOintViewSet, basename='budget')
router.register(r'milestones', endPointApiViews.MilestonesViewSet, basename='milestones')
router.register(r'milestones', endPointApiViews.MilestonesViewSet, basename='milestones')
router.register(r'leave', leaveApiViews.LeaveViewSet, basename='leave')
# router.register(r'settings', UserSettingsDetail.as_view(), basename='settings')

urlpatterns += [
    path('api/', include((router.urls, 'api_app'), namespace='api')),
    path('api/settings/', include('settings.urls_api')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

if settings.DEBUG:
    # Static file access
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Media file access
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('sendtest', SendTestView, name='testmail'),]
