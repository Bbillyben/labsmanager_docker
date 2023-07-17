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
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

User = get_user_model()
   
admin.site.unregister(User)
admin.site.register(User, LabsUserAdmin)