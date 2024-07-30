
from django.urls import include, path, re_path
from . import views, apiviews

urlpatterns = [
    # User settings
    re_path(r'^user/', include([
        # User Settings Detail
        re_path(r'^(?P<key>\w+)/',apiviews.UserSettingsDetail.as_view(), name='api-user-setting-detail'),

        # User Settings List
        re_path(r'^.*$', apiviews.UserSettingsList.as_view(), name='api-user-setting-list'),
    ])),
    # Project settings
    re_path(r'^project/', include([
        # User Settings Detail
        re_path(r'^(?P<key>\w+)/',apiviews.ProjectSettingsDetail.as_view(), name='api-project-setting-detail'),

        # User Settings List
        re_path(r'^.*$', apiviews.ProjectSettingsList.as_view(), name='api-project-setting-list'),
    ])),
    # Global settings
    re_path(r'^global/', include([
        # Global Settings Detail
        re_path(r'^(?P<key>\w+)/', apiviews.GlobalSettingsDetail.as_view(), name='api-global-setting-detail'),

        # Global Settings List
        re_path(r'^.*$', apiviews.GlobalSettingsList.as_view(), name='api-global-setting-list'),
    ])),
]