"""Admin for plugin app."""

from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime
from django import forms
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.template.response import TemplateResponse
from django.utils import timezone

from plugin import registry as pl_registry
from plugin.models import PluginSetting, UserPluginSetting, PluginConfig, PluginAccessToken
from plugin.tokens import TokenError, available_scopes, create_token, revoke_token


def plugin_update(queryset, new_status: bool):
    """General function for bulk changing plugins."""
    apps_changed = False

    # Run through all plugins in the queryset as the save method needs to be overridden
    for plugin in queryset:
        if plugin.active is not new_status:
            plugin.active = new_status
            plugin.save(no_reload=True)
            apps_changed = True

    # Reload plugins if they changed
    if apps_changed:
        pl_registry.reload_plugins()


@admin.action(description='Activate plugin(s)')
def plugin_activate(modeladmin, request, queryset):
    """Activate a set of plugins."""
    plugin_update(queryset, True)


@admin.action(description='Deactivate plugin(s)')
def plugin_deactivate(modeladmin, request, queryset):
    """Deactivate a set of plugins."""
    plugin_update(queryset, False)


class PluginSettingInline(admin.TabularInline):
    """Inline admin class for PluginSetting."""

    model = PluginSetting

    read_only_fields = ['key']

    def has_add_permission(self, request, obj):
        """The plugin settings should not be meddled with manually."""
        return False

class UserPluginSettingInline(admin.TabularInline):
    """Inline admin class for PluginSetting."""

    model = UserPluginSetting

    read_only_fields = ['key']

    def has_add_permission(self, request, obj):
        """The plugin settings should not be meddled with manually."""
        return False

class PluginConfigAdmin(admin.ModelAdmin):
    """Custom admin with restricted id fields."""

    readonly_fields = ['key', 'name',]
    list_display = [
        'name',
        'key',
        'active',
        'is_builtin',
        'is_sample',
    ]
    list_filter = ['active']
    actions = [plugin_activate, plugin_deactivate]
    inlines = [PluginSettingInline, UserPluginSettingInline]
    # exclude = ['metadata']


# class NotificationUserSettingAdmin(admin.ModelAdmin):
#     """Admin class for NotificationUserSetting."""

#     model = models.NotificationUserSetting

#     read_only_fields = ['key']

#     def has_add_permission(self, request):
#         """Notifications should not be changed."""
#         return False


admin.site.register(PluginConfig, PluginConfigAdmin)


class PluginTokenCreateForm(forms.Form):
    plugin = forms.ModelChoiceField(queryset=PluginConfig.objects.none())
    name = forms.CharField(max_length=150)
    scopes = forms.MultipleChoiceField(required=False)
    expires_at = forms.SplitDateTimeField(required=False, widget=AdminSplitDateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = {}
        configs = []
        for plugin in pl_registry.with_mixin('token'):
            try:
                scopes = available_scopes(plugin, 'plugin')
            except TokenError:
                continue
            configs.append(plugin.slug)
            for name, info in scopes.items():
                choices.setdefault(name, f"{name} — {info.get('label', name)}")
        self.fields['plugin'].queryset = PluginConfig.objects.filter(key__in=configs, active=True)
        self.fields['scopes'].choices = sorted(choices.items())

    def clean(self):
        data = super().clean()
        config = data.get('plugin')
        if config:
            plugin = pl_registry.get_plugin(config.key)
            try:
                allowed = available_scopes(plugin, 'plugin')
                if any(scope not in allowed for scope in data.get('scopes', [])):
                    self.add_error('scopes', 'This scope is not available for the selected plugin.')
            except (TokenError, AttributeError):
                self.add_error('plugin', 'This plugin does not allow technical tokens.')
        return data

    def clean_expires_at(self):
        expires_at = self.cleaned_data['expires_at']
        if expires_at is not None and expires_at <= timezone.now():
            raise forms.ValidationError('Expiration must be in the future.')
        return expires_at


@admin.action(description='Revoke selected plugin tokens')
def revoke_plugin_tokens(modeladmin, request, queryset):
    for token in queryset:
        revoke_token(token)


class TokenStatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'token_status'

    def lookups(self, request, model_admin):
        return (('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked'))

    def queryset(self, request, queryset):
        status = self.value()
        if status == 'revoked':
            return queryset.filter(revoked_at__isnull=False)
        if status == 'expired':
            return queryset.filter(revoked_at__isnull=True, expires_at__lte=timezone.now())
        if status == 'active':
            return queryset.filter(revoked_at__isnull=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        return queryset

class TokenUserFilter(admin.SimpleListFilter):
    title = 'User Token'
    parameter_name = 'token_user'

    def lookups(self, request, model_admin):
            return (('user', 'User'), ('plugin', 'Plugin'))

    def queryset(self, request, queryset):
            status = self.value()
            if status == 'user':
                return queryset.filter(kind=PluginAccessToken.Kind.USER)
            if status == 'plugin':
                return queryset.filter(kind=PluginAccessToken.Kind.PLUGIN)
            return queryset

class PluginTokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'plugin', 'public_id', 'user', 'token_status', 'created_at', 'expires_at', 'revoked_at', 'last_used_at')
    list_filter = ('plugin', TokenStatusFilter, TokenUserFilter, 'created_at', 'expires_at')
    search_fields = ('name', 'public_id', 'plugin__key')
    actions = (revoke_plugin_tokens,)
    fields = ('name', 'plugin', 'public_id', 'scopes', 'created_at', 'expires_at', 'revoked_at', 'last_used_at')
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Status')
    def token_status(self, obj):
        if obj.revoked_at is not None:
            return 'Revoked'
        if obj.expires_at is not None and obj.expires_at <= timezone.now():
            return 'Expired'
        return 'Active'

    def add_view(self, request, form_url='', extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = PluginTokenCreateForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            plugin = pl_registry.get_plugin(form.cleaned_data['plugin'].key)
            try:
                token, secret = create_token(plugin, kind='plugin', name=form.cleaned_data['name'],
                                             scopes=form.cleaned_data['scopes'], expires_at=form.cleaned_data['expires_at'])
            except (TokenError, AttributeError) as error:
                form.add_error(None, str(error))
            else:
                response = TemplateResponse(request, 'admin/plugin/token_created.html', {
                    **self.admin_site.each_context(request), 'title': 'Plugin token created',
                    'token': token, 'secret': secret, 'opts': self.model._meta,
                })
                response['Cache-Control'] = 'no-store'
                return response
        return TemplateResponse(request, 'admin/plugin/token_add.html', {
            **self.admin_site.each_context(request), 'title': 'Add plugin token',
            'form': form, 'media': self.media + form.media, 'opts': self.model._meta,
        })


admin.site.register(PluginAccessToken, PluginTokenAdmin)
# admin.site.register(models.NotificationUserSetting, NotificationUserSettingAdmin)
