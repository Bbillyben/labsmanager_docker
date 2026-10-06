from django.contrib import admin
from .models import EmployeeWordReport, ProjectWordReport, EmployeePDFReport, ProjectPDFReport

# Register your models here.
# @admin.register(EmployeeWordReport)
class EmployeeWordReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'download_link', 'revision', 'description', 'filename_pattern','enabled',)
    readonly_fields = ('download_link','revision')  # Ajouter le lien en lecture seule
    fields = [
        ('name', 'revision'), 
        'description', 
        'enabled', 
        'filename_pattern', 
        'template', 
        'download_link',
    ] 

admin.site.register(EmployeeWordReport, EmployeeWordReportAdmin)
admin.site.register(EmployeePDFReport, EmployeeWordReportAdmin)
admin.site.register(ProjectWordReport, EmployeeWordReportAdmin)
admin.site.register(ProjectPDFReport, EmployeeWordReportAdmin)