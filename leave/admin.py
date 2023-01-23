from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Leave_Type, Leave


class LeaveItemAdmin(admin.ModelAdmin):
    fields = ('employee','type', 'start_date', 'end_date','comment',)
    list_display = ('employee','type', 'start_date', 'end_date',)
    list_filter = ('employee', 'type', 'start_date', 'end_date',)

# Register your models here.
admin.site.register(Leave_Type)
admin.site.register(Leave, LeaveItemAdmin)