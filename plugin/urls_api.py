
from django.urls import include, path, re_path
from . import  apiviews

urlpatterns = [
    path('', apiviews.PluginList.as_view(), name='api-plugin-list'),
    # Plugin settings
    # re_path(r'^setting/', include([
    #     # User Settings Detail
    #     # re_path(r'^(?P<key>\w+)/',apiviews.UserSettingsDetail.as_view(), name='api-user-setting-detail'),

    #     # Plugin Settings List
    #     re_path(r'^.*$', apiviews.PluginConfigViewSet.as_view(), name='api-plugin-setting-list'),
    # ])),
    path(
        '<str:plugin>/',
        include([
            path(
                'settings/',
                include([
                    re_path(
                        r'^(?P<key>\w+)/',
                        apiviews.PluginSettingDetail.as_view(),
                        name='api-plugin-setting-detail',
                    ),
                    # path(
                    #     '',
                    #     PluginAllSettingList.as_view(),
                    #     name='api-plugin-settings',
                    # ),
                ]),
            ),
            # path(
            #     'metadata/',
            #     PluginMetadataView.as_view(),
            #     {'model': PluginConfig, 'lookup_field': 'key'},
            #     name='api-plugin-metadata',
            # ),
            # path(
            #     'activate/',
            #     PluginActivate.as_view(),
            #     name='api-plugin-detail-activate',
            # ),
            # path(
            #     'uninstall/',
            #     PluginUninstall.as_view(),
            #     name='api-plugin-uninstall',
            # ),
            # path('', PluginDetail.as_view(), name='api-plugin-detail'),
        ]),
    ),
]