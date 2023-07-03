from django.contrib import admin

from .models import favorite, subscription
class favoriteAdmin(admin.ModelAdmin):
    #list_filter = (get_generic_foreign_key_filter(u'content_type'),)
    list_display = ('user', 'content_type', 'object_id', 'content_object',)   
    
admin.site.register(favorite, favoriteAdmin)
admin.site.register(subscription, favoriteAdmin)