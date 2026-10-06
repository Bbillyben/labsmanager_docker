from django.contrib import admin
from .models import UserNotification

class UserNotificationAdmin(admin.ModelAdmin):
    #list_filter = (get_generic_foreign_key_filter(u'content_type'),)
    list_display = ('source_content_type', 'source_object', 'user', 'action_type', 'creation', 'send', 'is_done',)   
    
    @admin.display(boolean=True, description='Done')
    def is_done(self, obj):
        return obj.done
admin.site.register(UserNotification, UserNotificationAdmin)