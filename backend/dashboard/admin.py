from .models import Dashboard

from django.contrib import admin


class DashboardAdmin(admin.ModelAdmin):
    """Keep Employee type administration textual."""
    model = Dashboard
    list_display = ('owner', 'name',  'icon' , 'scope', 'is_default')

    
admin.site.register(Dashboard, DashboardAdmin)