from django.contrib import admin
from labsmanager.admin import GenericInfoTypeAdmin

from .models import OrganizationInfosType, OrganizationInfos, ContactType, ContactInfoType, Contact, ContactInfo


class ContactInfoInline(admin.TabularInline):
    model = ContactInfo
    extra = 0
    
class ContactAdmin(admin.ModelAdmin):
    list_display = ( 'first_name', 'last_name','type','content_object',)
    list_filter=('type' ,)
    inlines = [ContactInfoInline,] 
    
admin.site.register(OrganizationInfosType, GenericInfoTypeAdmin)
admin.site.register(OrganizationInfos)
admin.site.register(ContactType)
admin.site.register(ContactInfoType, GenericInfoTypeAdmin)
admin.site.register(Contact, ContactAdmin)


