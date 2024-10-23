from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from faicon import widgets

class GenericInfoTypeAdmin(admin.ModelAdmin):
    list_display = ( 'name', 'get_icon',)
    
    @admin.display(description='Icon')
    def get_icon(self, obj):
        icon=widgets.parse_icon(str(obj.icon))
        if isinstance(icon, widgets.Icon):
            return icon.icon_html()
        return obj.icon
    class Media:
        css = {
            'all':('/static/fontawesome/css/all.css','/static/css/adminsmall.css',), 
        }
        js = (
            'script/jquery-3.6.1.min.js', # jquery
        )

     
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
class LabsUserAdmin(UserAdmin):
    """Custom admin page for the User model.

    Hides the "permissions" view as this is now handled
    entirely by groups and RuleSets.

    (And it's confusing!)
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'last_login',)  # display last connection for each user in user admin panel.
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups'),
        }),
        (_('User Permissions'), {
            'fields': ('user_permissions',),
        }),
         
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

User = get_user_model()


# generic content type filter
from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

class UsedContenTypeFilter(admin.SimpleListFilter):
    title = _("Current Content Type ")
    parameter_name = "used_cr"
    
    def lookups(self, request, model_admin):
        
        content_types = model_admin.model.objects.values('content_type').annotate(count=Count('content_type')).order_by('content_type')

        CT_LIST = [(ct['content_type'], str(ContentType.objects.get(id=ct['content_type']))) for ct in content_types]

        return CT_LIST
        
    def queryset(self, request, queryset):
        
        if self.value() is None:
            return queryset
        
        qs = queryset.filter(content_type=self.value())
        return qs
   
admin.site.unregister(User)
admin.site.register(User, LabsUserAdmin)