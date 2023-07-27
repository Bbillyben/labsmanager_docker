from django.contrib import admin
from .models import EmployeeWordReport, ProjectWordReport, EmployeePDFReport, ProjectPDFReport

# Register your models here.
# @admin.register(EmployeeWordReport)
class EmployeeWordReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'revision', 'description', 'filename_pattern','enabled',)



admin.site.register(EmployeeWordReport, EmployeeWordReportAdmin)
admin.site.register(EmployeePDFReport, EmployeeWordReportAdmin)
admin.site.register(ProjectWordReport, EmployeeWordReportAdmin)
admin.site.register(ProjectPDFReport, EmployeeWordReportAdmin)