from django.contrib import admin
from .models import EmployeeWordReport

# Register your models here.
# @admin.register(EmployeeWordReport)
class EmployeeWordReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'revision', 'description', 'filename_pattern','enabled',)



admin.site.register(EmployeeWordReport, EmployeeWordReportAdmin)