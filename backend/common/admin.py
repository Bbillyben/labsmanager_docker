from django.contrib import admin

from .models import favorite, subscription
from labsmanager.admin import UsedContenTypeFilter
class favoriteAdmin(admin.ModelAdmin):
    #list_filter = (get_generic_foreign_key_filter(u'content_type'),)
    list_display = ('user', 'content_type', 'object_id', 'content_object',)   
    list_filter=('user', UsedContenTypeFilter ,)

admin.site.register(favorite, favoriteAdmin)
admin.site.register(subscription, favoriteAdmin)