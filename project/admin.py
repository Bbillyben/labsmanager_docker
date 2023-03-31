from django.contrib import admin
from labsmanager.admin import GenericInfoTypeAdmin
from project.models import Project, Institution, Institution_Participant, Participant, GenericInfoTypeProject, GenericInfoProject
from django.contrib.sessions.models import Session
import pprint

class InstitutionParticipantInLine(admin.TabularInline):
    model=Institution_Participant
    extra=0
    
class ParticipantInLine(admin.TabularInline):
    model=Participant
    extra=0
    
class GenericInfoInline(admin.TabularInline):
    model = GenericInfoProject
    extra = 0 
    
class ProjectAdmin(admin.ModelAdmin):
    inlines = [GenericInfoInline, InstitutionParticipantInLine, ParticipantInLine]
    list_display = ('name', 'start_date', 'end_date', 'status')
    list_filter=('status' ,'start_date', 'end_date')
    
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name')
    
    
    


# class SessionAdmin(admin.ModelAdmin):
#     def _session_data(self, obj):
#         return obj.get_decoded()
#     list_display = ['session_key', '_session_data', 'expire_date']
    
class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return pprint.pformat(obj.get_decoded()).replace('\n', '<br>\n')
    _session_data.allow_tags=True
    list_display = ['session_key', '_session_data', 'expire_date']
    readonly_fields = ['_session_data']
    exclude = ['session_data']
    date_hierarchy='expire_date'
    
admin.site.register(Session, SessionAdmin)
# Register your models here.
admin.site.register(Project, ProjectAdmin)
admin.site.register(Institution, InstitutionAdmin)

admin.site.register(GenericInfoTypeProject, GenericInfoTypeAdmin)


