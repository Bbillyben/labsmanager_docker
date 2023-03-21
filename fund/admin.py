from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from fund.models import Cost_Type, Fund_Institution, Fund_Item, Fund, Budget, AmountHistory
from import_export.admin import ImportExportModelAdmin
from .resources import FundItemAdminResource

class CostTypeAdmin(admin.ModelAdmin):
    list_display = ('name','short_name', 'in_focus',)

class FundInstitutionAdmin(admin.ModelAdmin):
    list_display = ('name','short_name',)
    
class FundTypeInline(admin.TabularInline):
    model=Fund_Item
    extra=0

class FundItemAdmin(ImportExportModelAdmin):

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
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('fund','cost_type', 'amount', 'emp_type', 'employee', 'quotity', 'get_contract_type',)
    list_filter = ('cost_type', 'emp_type','contract_type',)
    
    def get_contract_type(self, obj):
        return ",  ".join([p.name for p in obj.contract_type.all()])
 
 
 
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

def get_generic_foreign_key_filter(title, parameter_name=u'', separator='-', content_type_id_field='content_type', object_id_field='object_id') :

    class GenericForeignKeyFilter(admin.SimpleListFilter):

        def __init__(self, request, params, model, model_admin):
            self.separator = separator
            self.title = title
            self.parameter_name = u'generic_foreign_key_' + parameter_name
            super(GenericForeignKeyFilter, self).__init__(request, params, model, model_admin)

        def lookups(self, request, model_admin):
            qs = model_admin.model.objects.all()\
                .order_by(content_type_id_field, object_id_field)\
                .distinct(content_type_id_field, object_id_field)\
                .values_list(content_type_id_field, object_id_field)

            return [
                (
                    '{1}{0.separator}{2}'.format(self, *content_type_and_obj_id_pair),
                    ContentType.objects
                        .get(id=content_type_and_obj_id_pair[0])
                        .model_class()
                        .objects.get(pk=content_type_and_obj_id_pair[1])
                        .__str__()
                )
                for content_type_and_obj_id_pair
                in qs
            ]

        def queryset(self, request, queryset):
            try :
                content_type_id, object_id = self.value().split(self.separator)
                return queryset.filter(**({
                    content_type_id_field:content_type_id,
                    object_id_field:object_id
                }))
            except:
                return queryset

    return GenericForeignKeyFilter

def get_content_type_filter(title, parameter_name=u'', separator='-', content_type_id_field='content_type') :
    
    class ContentTypeFilter(admin.SimpleListFilter):
        def __init__(self, request, params, model, model_admin):
            self.title = title
            self.parameter_name = u'content_type_' + parameter_name
            super(ContentTypeFilter, self).__init__(request, params, model, model_admin)
            
        def lookups(self, request, model_admin):
            qs = model_admin.model.objects.all().distinct(content_type_id_field).values(content_type_id_field)
            ctIn=ContentType.objects.filter(id__in=qs)
            print("  - qs:"+str(qs)) 
            return [
                (
                    str(ct.app_label)+"."+str(ct.model),
                    ct.model_class().__str__()
                )
                for ct
                in qs
            ]
        
        
        
        def queryset(self, request, queryset):
            try :
                return queryset.filter(**({
                    content_type_id_field:self.value(),
                }))
            except:
                return queryset
    return ContentTypeFilter

class AmountHistoryAdmin(admin.ModelAdmin):
    #list_filter = (get_generic_foreign_key_filter(u'content_type'),)
    list_filter = ('value_date',get_content_type_filter(u'content_type'))
    list_display = ('created_at', 'content_type', 'object_id', 'content_object', 'amount', 'delta', 'value_date')   

admin.site.register(Fund, FundAdmin)
admin.site.register(Fund_Institution, FundInstitutionAdmin)
admin.site.register(Fund_Item, FundItemAdmin)
admin.site.register(Cost_Type, CostTypeAdmin)
admin.site.register(Budget, BudgetAdmin)
admin.site.register(AmountHistory, AmountHistoryAdmin)