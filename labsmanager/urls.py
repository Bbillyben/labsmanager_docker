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
from .views import IndexView , redirectIndexView, get_filters_lists
from settings.apiviews import UserSettingsDetail
from rest_framework import routers
from . import apiviews #UserViewSet, GroupViewSet, EmployeeViewSet, ProjectViewSet, FundViewSet
from expense import apiviews as contractApiViews
from project import apiviews as projectApiViews
from fund import apiviews as fundApiViews
from staff import apiviews as staffApiViews
from endpoints import apiviews as endPointApiViews
from leave import apiviews as leaveApiViews
from common import apiviews as commonApiViews
from settings import apiviews as settingAppiViews
from infos import apiviews as infoApiViews
from django.conf.urls.i18n import i18n_patterns
from django_js_reverse import views as jsrev_views


urlpatterns = [
    path('filter_code_list', get_filters_lists, name='filter_code_list'),
    path('admin/', admin.site.urls),
    re_path(r'^index/', IndexView.as_view(), name='index_explicit'),
    path('', IndexView.as_view(), name='index'),
    path('staff/', include('staff.urls'), name='staff'),                  # For Staff models
    path('project/', include('project.urls')),              # for project model
    path('fund/', include('fund.urls')),              # for project model
    path('expense/', include('expense.urls'), name='expense'),              # for project model
    path('dashboard/', include('dashboard.urls')),
    path('settings/', include('settings.urls')),
    path('milestones/', include('endpoints.urls')),
    path('calendar/', include('leave.urls')),
    path('common/', include('common.urls')),
    path('reports/', include('reports.urls')),
    path('infos/', include('infos.urls')),
    path('import/', include('import.urls')),
]
#  Authentications : 
urlpatterns += [
    #path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/', include('allauth.urls')),
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
#router.register(r'fundlist', fundApiViews.FundListViewSet, basename='fundlist')
router.register(r'settinglist', settingAppiViews.SettingListViewSet, basename='settinglist')
router.register(r'funditem', fundApiViews.FundItemViewSet, basename='funditem')
router.register(r'contract', contractApiViews.ContractViewSet, basename='contract')
router.register(r'expense', contractApiViews.ExpensePOintViewSet, basename='expense')
router.register(r'budget', fundApiViews.BudgetViewSet, basename='budget')
router.register(r'contribution', fundApiViews.ContributionViewSet, basename='contribution')
router.register(r'milestones', endPointApiViews.MilestonesViewSet, basename='milestones')
router.register(r'milestones', endPointApiViews.MilestonesViewSet, basename='milestones')
router.register(r'leave', leaveApiViews.LeaveViewSet, basename='leave')
router.register(r'favorite', commonApiViews.favoriteViewSet, basename='favorite')
router.register(r'subscription', commonApiViews.subscriptionViewSet, basename='subscription')
router.register(r'organization', infoApiViews.organisationViewSet, basename='organization')
# router.register(r'settings', UserSettingsDetail.as_view(), basename='settings')

urlpatterns += [
    path('api/', include((router.urls, 'api_app'), namespace='api')),
    path('api/settings/', include('settings.urls_api')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

urlpatterns += [
    path('faicon/', include('faicon.urls')),
]

from .views import serve_protected_media
urlpatterns += [
    path('report/<path:path>', serve_protected_media, name='serve_protected_media'),
]


if settings.DEBUG:
    # Static file access
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Media file access
    #urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    from labsmanager.tasks import create_report
    urlpatterns += [path('testTask', create_report, name='testTask'),]



# Admin Site Customisation
from labsmanager import settings
admin.site.site_header  =  settings.ADMIN_HEADER
admin.site.site_title  =  settings.ADMIN_SITE_TITLE
admin.site.index_title  =  settings.ADMIN_INDEX_TITLE