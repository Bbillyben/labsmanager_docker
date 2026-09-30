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
    list_display = ( 'name', 'content_type','content_object','creator','visibility',)
    list_filter=(UsedContenTypeFilter ,)
    readonly_fields = ('creator',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        from .api_v1 import legacy_visible_notes
        return super().get_queryset(request).filter(pk__in=legacy_visible_notes(request.user).values('pk'))

admin.site.register(GenericNote, noteAdmin)

admin.site.register(OrganizationInfosType, OrgaInfoTypeAdmin)
admin.site.register(OrganizationInfos)
admin.site.register(ContactType)
admin.site.register(ContactInfoType, OrgaInfoTypeAdmin)
admin.site.register(Contact, ContactAdmin)


