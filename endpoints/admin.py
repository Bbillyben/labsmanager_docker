from django.utils.translation import gettext_lazy as _
from django.contrib import admin
from .models import Milestones

from project.models import Project

class EmployeeProjectFundListFitler(admin.SimpleListFilter):
    title = _("Attribution")
    parameter_name = "employee"
    
    def lookups(self, request, model_admin):
        employees = Milestones.objects.all().values_list("employee__id", "employee__first_name", "employee__last_name").distinct()
        return [(emp_id, "%s %s"%(emp_fname, emp_lname)) for emp_id, emp_fname, emp_lname in employees if emp_id is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(employee__id=self.value())
        return queryset
    
    
class MilestoneProjectFundListFitler(admin.SimpleListFilter):
    title = _("Project")
    parameter_name = "project"
    
    def lookups(self, request, model_admin):
        exps = Milestones.objects.all().values("project")
        pjl = Project.objects.filter(pk__in=exps)
        return [
                (
                    ct.pk,
                    ct.__str__()
                )
                for ct
                in pjl
            ]
        
    def queryset(self, request, queryset):
        
        if self.value()==None:
            return queryset
        return queryset.filter(project = self.value()) 

class MilestonesAdmin(admin.ModelAdmin):
    list_display = ('get_proj_name', 'name', 'desc', 'deadline_date', 'type', 'quotity', 'status', 'get_employee_list')
    list_filter=('status' ,'deadline_date', EmployeeProjectFundListFitler, MilestoneProjectFundListFitler)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.distinct()
    
    def get_proj_name(self, obj):
        return obj.project.__str__()
    get_proj_name.short_description = _('Project')
    get_proj_name.admin_order_field = 'project__name'
    
    def get_employee_list(self, obj):
        return ", ".join(emp.user_name for emp in obj.employee.all())
    get_employee_list.short_description = _('Attribution')
        
    
    
admin.site.register(Milestones, MilestonesAdmin)
