from django.contrib import admin
from labsmanager.admin import GenericInfoTypeAdmin

from .models import OrganizationInfosType, OrganizationInfos, ContactType, ContactInfoType, Contact, ContactInfo, GenericNote


class ContactInfoInline(admin.TabularInline):
    model = ContactInfo
    extra = 0
    
class ContactAdmin(admin.ModelAdmin):
    list_display = ( 'first_name', 'last_name','type','content_object',)
    list_filter=('type' ,)
    inlines = [ContactInfoInline,] 

class OrgaInfoTypeAdmin(GenericInfoTypeAdmin):
    list_display = ( 'name', 'get_icon', "type")
    
    
# for notes, try a specific filter for content type
from labsmanager.admin import UsedContenTypeFilter
    
class noteAdmin(admin.ModelAdmin):
    list_display = ( 'name', 'content_type','content_object',)
    list_filter=(UsedContenTypeFilter ,)

admin.site.register(GenericNote, noteAdmin)

admin.site.register(OrganizationInfosType, OrgaInfoTypeAdmin)
admin.site.register(OrganizationInfos)
admin.site.register(ContactType)
admin.site.register(ContactInfoType, OrgaInfoTypeAdmin)
admin.site.register(Contact, ContactAdmin)


