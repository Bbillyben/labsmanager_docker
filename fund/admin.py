from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from fund.models import Cost_Type, Fund_Institution, Fund_Item, Fund
from import_export.admin import ImportExportModelAdmin
from .resources import FundItemAdminResource

class CostTypeAdmin(admin.ModelAdmin):
    list_display = ('name','short_name')

class FundTypeInline(admin.TabularInline):
    model=Fund_Item
    extra=0

class FundItemAdmin(ImportExportModelAdmin):
    fields = ('project', 
                      'funder',
                      'institution',
                      'start_date',
                      'end_date',
                      'type',
                      'ref',
                      'amount',
                      'expense',
                      'available',
                      )
    list_display = ('get_funder_name','get_proj_name', 'get_institution', 'type', 'amount',)
    list_filter = ('fund__funder', 'fund__project', 'fund__institution', 'type',)
    resource_classes = [FundItemAdminResource]  
    
    def get_proj_name(self, obj):
        return obj.fund.project.name
    get_proj_name.short_description = _('Project')
    get_proj_name.admin_order_field = 'fund__project_name'
    
    
    def get_funder_name(self, obj):
        return obj.fund.funder.short_name
    get_funder_name.short_description = _('Funder')
    get_funder_name.admin_order_field = 'fund__funder_name'
    
    def get_institution(self, obj):
        return obj.fund.institution.short_name
    get_institution.short_description = _('Institution')
    get_institution.admin_order_field = 'fund__institution_name'
    
    
class FundAdmin(admin.ModelAdmin):
    list_display = ('get_proj_name','get_funder_name','get_manager_name', 'ref',)
    inlines = [FundTypeInline]
    
    def get_proj_name(self, obj):
        return obj.project.name
    get_proj_name.short_description = _('Project')
    get_proj_name.admin_order_field = 'fund__project_name'
    
    def get_funder_name(self, obj):
        return obj.funder.short_name
    get_funder_name.short_description = _('Funder')
    get_funder_name.admin_order_field = 'fund__funder_name'
    
    def get_manager_name(self, obj):
        return obj.institution.short_name
    get_manager_name.short_description = _('Manager')
    get_manager_name.admin_order_field = 'fund__manager_name'
    
# Register your models here.
admin.site.register(Cost_Type, CostTypeAdmin)
admin.site.register(Fund_Institution, CostTypeAdmin)
admin.site.register(Fund, FundAdmin)
admin.site.register(Fund_Item, FundItemAdmin)