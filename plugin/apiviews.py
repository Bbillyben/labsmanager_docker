from typing import Optional
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, permissions, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound

from django_filters import rest_framework as rest_filters

from . import serializers
from .models import PluginConfig, PluginSetting
from . import LabManagerPlugin

class PluginFilter(rest_filters.FilterSet):
    """Filter for the PluginConfig model.

    Provides custom filtering options for the FilterList API endpoint.
    """

    class Meta:
        """Meta for the filter."""

        model = PluginConfig
        fields = ['active']

    mixin = rest_filters.CharFilter(
        field_name='mixin', method='filter_mixin', label='Mixin'
    )

    def filter_mixin(self, queryset, name, value):
        """Filter by implement mixin.

        - A comma-separated list of mixin names can be provided.
        - Only plugins which implement all of the provided mixins will be returned.
        """
        matches = []
        mixins = [x.strip().lower() for x in value.split(',') if x]

        for result in queryset:
            match = True

            for mixin in mixins:
                if mixin not in result.mixins():
                    match = False
                    break

            if match:
                matches.append(result.pk)

        return queryset.filter(pk__in=matches)

    builtin = rest_filters.BooleanFilter(
        field_name='builtin', label='Builtin', method='filter_builtin'
    )

    def filter_builtin(self, queryset, name, value):
        """Filter by 'builtin' flag."""
        matches = []

        for result in queryset:
            if result.is_builtin() == value:
                matches.append(result.pk)

        return queryset.filter(pk__in=matches)

    sample = rest_filters.BooleanFilter(
        field_name='sample', label='Sample', method='filter_sample'
    )

    def filter_sample(self, queryset, name, value):
        """Filter by 'sample' flag."""
        matches = []

        for result in queryset:
            if result.is_sample() == value:
                matches.append(result.pk)

        return queryset.filter(pk__in=matches)

    installed = rest_filters.BooleanFilter(
        field_name='installed', label='Installed', method='filter_installed'
    )

    def filter_installed(self, queryset, name, value):
        """Filter by 'installed' flag."""
        matches = []

        for result in queryset:
            if result.is_installed() == value:
                matches.append(result.pk)

        return queryset.filter(pk__in=matches)
class PluginList(generics.ListAPIView):
    queryset = PluginConfig.objects.all()
    lookup_field = 'key'
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = PluginFilter
    serializer_class = serializers.PluginConfigSerializer
    filterset_fields = ['active']

    ordering_fields = ['key', 'name', 'active']

    ordering = ['-active', 'name', 'key']

    search_fields = ['key', 'name']

class PluginSettingDetail(generics.RetrieveUpdateAPIView):
    """Detail endpoint for a plugin-specific setting.

    Note that these cannot be created or deleted via the API
    """

    queryset = PluginSetting.objects.all()
    serializer_class = serializers.PluginSettingSerializer

    def get_object(self):
        """Lookup the plugin setting object, based on the URL.

        The URL provides the 'slug' of the plugin, and the 'key' of the setting.
        Both the 'slug' and 'key' must be valid, else a 404 error is raised
        """
        setting_key = self.kwargs['key']

        # Look up plugin
        plugin = check_plugin(self.kwargs.get('plugin', None), None)

        settings = getattr(plugin, 'settings', {})

        if setting_key not in settings:
            raise NotFound(
                detail=f"Plugin '{plugin.slug}' has no setting matching '{setting_key}'"
            )

        return PluginSetting.get_setting_object(
            setting_key, plugin=plugin.plugin_config()
        )

    # Staff permission required
    permission_classes = [permissions.IsAuthenticated]

class PluginConfigViewSet(viewsets.ModelViewSet):
    queryset = PluginConfig.objects.all()
    serializer_class = serializers.PluginConfigSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @action(methods=['patch'], detail=False, url_path='(?P<plugin>[^/.]+)/settings/(?P<setting>[^/.]+)', url_name='plugin_setting')
    def set_plugin_setting(self, request, plugin, setting):
        plugin_ob = check_plugin(plugin, None)
        return HttpResponse("Ok", status=200)




def check_plugin(plugin_slug: Optional[str], plugin_pk: Optional[int]) -> LabManagerPlugin:
    """Check that a plugin for the provided slug exists and get the config.

    Args:
        plugin_slug (str): Slug for plugin.
        plugin_pk (int): Primary key for plugin.

    Raises:
        NotFound: If plugin is not installed
        NotFound: If plugin is not correctly registered
        NotFound: If plugin is not active

    Returns:
        LabManagerPlugin: The config object for the provided plugin.
    """
    # Make sure that a plugin reference is specified
    if plugin_slug is None and plugin_pk is None:
        raise NotFound(detail='Plugin not specified')

    # Define filter
    filters = {}
    if plugin_slug:
        filters['key'] = plugin_slug
    elif plugin_pk:
        filters['pk'] = plugin_pk
    ref = plugin_slug or plugin_pk

    # Check that the 'plugin' specified is valid
    try:
        plugin_cgf = PluginConfig.objects.filter(**filters).first()
    except PluginConfig.DoesNotExist:
        raise NotFound(detail=f"Plugin '{ref}' not installed")

    if plugin_cgf is None:
        # This only occurs if the plugin mechanism broke
        raise NotFound(detail=f"Plugin '{ref}' not installed")  # pragma: no cover

    # Check that the plugin is activated
    if not plugin_cgf.active:
        raise NotFound(detail=f"Plugin '{ref}' is not active")

    plugin = plugin_cgf.plugin

    if not plugin:
        raise NotFound(detail=f"Plugin '{ref}' not installed")

    return plugin

class PluginActivate(generics.UpdateAPIView):
    """Endpoint for activating a plugin.

    - PATCH: Activate a plugin

    Pass a boolean value for the 'active' field.
    If not provided, it is assumed to be True,
    and the plugin will be activated.
    """

    queryset = PluginConfig.objects.all()
    serializer_class = serializers.PluginActivateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'key'
    lookup_url_kwarg = 'plugin'

    def get_object(self):
        """Returns the object for the view."""
        if self.request.data.get('pk', None):
            return self.queryset.get(pk=self.request.data.get('pk'))
        return super().get_object()

    def perform_update(self, serializer):
        """Activate the plugin."""
        serializer.save()
        
class PluginReload(generics.CreateAPIView):
    """Endpoint for reloading all plugins."""

    queryset = PluginConfig.objects.none()
    serializer_class = serializers.PluginReloadSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        """Saving the serializer instance performs plugin installation."""
        return serializer.save()
    
    
#### FOR CalendarEvent Plugin *
from django.views.generic.base import View
from settings.accessor import get_global_setting
class PluginCalendarEventDispatcher(View):
    
    def post(self, request,*args, **kwargs):
        print("=====================================   PluginCalendarEventDispatcher [POST]    =====================================")
        from plugin import registry
        event_list = []
        for plugin in registry.with_mixin("calendarevent", active=True):
            plugin.get_event(request, event_list)
        return JsonResponse(event_list, safe=False)
    def get(self, request,*args, **kwargs):
        print("=====================================   PluginCalendarEventDispatcher [GET]    =====================================")
        from plugin import registry
        event_list = []
        for plugin in registry.with_mixin("calendarevent", active=True):
            plugin.get_event(request, event_list)
        return JsonResponse(event_list, safe=False)
    
# def get_calevent_mixin_events(request):
#     # print("------------------------------------------------------------------------------")
#     # print("-----------------          get_calevent_mixin_events   -----------------------")
#     # for k, v in request.GET.items():
#     #     print(f'  - {k} : {v}')
#     # print(f'  - user : {request.user}')
#     # print(f'  - method : {request.method}')
#     # print("------------------------------------------------------------------------------")
#     from plugin import registry
#     event_list = []
#     for plugin in registry.with_mixin("calendarevent", active=True):
#         plugin.get_event(request, event_list)
#     return JsonResponse(event_list, safe=False)