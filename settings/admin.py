from django.contrib import admin
from .models import LMUserSetting, LabsManagerSetting


class LMUserSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'key','value',)
    list_filter=('user' , 'key')

class LMSettingAdmin(admin.ModelAdmin):
    list_display = ('key','value',)
    
# Register your models here.
admin.site.register(LMUserSetting, LMUserSettingAdmin)
admin.site.register(LabsManagerSetting, LMSettingAdmin)
