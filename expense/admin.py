from django.contrib import admin
from expense.models import Expense_point, Expense, Contract_expense, Contract, Contract_type
from fund.models import Fund, Fund_Item
from django.utils.translation import gettext_lazy as _
from django.forms.models import BaseInlineFormSet
from django import forms
from django.urls import reverse
from django.utils.html import format_html

from import_export.admin import ImportExportModelAdmin

from .resources import ExpensePointResource, ExpenseResource


# # # # # # # # # // custom filters 
class ExpenseFundListFitler(admin.SimpleListFilter):
    title = _("Fund")
    parameter_name = "fund"
    
    def lookups(self, request, model_admin):
        exps = Expense.objects.all().values("fund_item")
        pjl = Fund.objects.filter(pk__in=exps)
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
        fl = Fund.objects.filter(pk = self.value())
        return queryset.filter(fund_item__in = fl)

class ContractExpenseFundListFitler(ExpenseFundListFitler):
    def lookups(self, request, model_admin):
        exps = Contract_expense.objects.all().values("fund_item")
        pjl = Fund.objects.filter(pk__in=exps)
        return [
                (
                    ct.pk,
                    ct.__str__()
                )
                for ct
                in pjl
            ]
##########################
    
class ContractExpenseInlineFormSet(BaseInlineFormSet):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in  kwargs:
            instance = kwargs['instance']
            for form in self.forms:
                form.fields['fund_item'] =forms.ModelChoiceField(
                    queryset=Fund.objects.filter(pk=instance.fund.pk),
                    initial=instance.fund,
                )

    
class Contract_expenseInline(admin.TabularInline):
    model=Contract_expense
    extra=0
    formset = ContractExpenseInlineFormSet
    fields =['expense_id', 'date', 'type', 'amount', 'status','fund_item']

    
class ContractAdmin(admin.ModelAdmin):
    list_display = ('__str__','get_proj_name','get_fund_name', 'start_date', 'end_date', 'quotity', 'status')
    list_filter=('status',)
    inlines = [Contract_expenseInline,]
     
    def get_proj_name(self, obj):
        return obj.fund.project.__str__()
    get_proj_name.short_description = _('Project')
    get_proj_name.admin_order_field = 'project__name'
    
    
    def get_fund_name(self, obj):
        return obj.fund.funder.__str__()
    get_fund_name.short_description = _('Funder')
    get_fund_name.admin_order_field = 'funder__short_name'
    
class ExpenseTimePointAdmin(ImportExportModelAdmin):
    list_display = ('fund','type','value_date', 'amount', 'entry_date')
    list_filter=('fund' ,'value_date', 'type')
    resource_classes = [ExpensePointResource]  
    list_display_links = None

class ExpenseAdmin(ImportExportModelAdmin):
    list_display = ('get_desc', 'fund_item','type', 'amount', 'get_status_display')
    list_filter=('date', 'type', ExpenseFundListFitler)
    resource_classes = [ExpenseResource]
    def get_queryset(self, request):
        return Expense.object_inherit.all().select_subclasses()
    
    def get_desc(self, obj):
        print(f"-----------> obj : {obj} is cont ins : {isinstance(obj, Contract_expense)}")
        if isinstance(obj, Contract_expense):
            desc =  obj.contract.employee
            url = reverse('admin:expense_contract_expense_change', args=[obj.pk])
        else:
            desc = obj.desc
            url = reverse('admin:expense_expense_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, desc)
    
    
    def get_status_display(self, obj):
        """Retourne l'étiquette de l'état pour un objet Expense"""
        return obj.get_status_display()  
    
    get_desc.short_description = _('Description')
    get_status_display.short_description = _('Status')
      
class ContractExpenseAdmin(ImportExportModelAdmin):
    list_display = ('get_contract_employee', 'fund_item','type', 'amount')
    list_filter=('date', 'type', ContractExpenseFundListFitler)
    
    def get_contract_employee(self, obj):
        return obj.contract.employee
    
    get_contract_employee.short_description = _('Employee')
    
# Register your models here.
admin.site.register(Expense, ExpenseAdmin)
admin.site.register(Contract_expense, ContractExpenseAdmin)
admin.site.register(Contract, ContractAdmin)
admin.site.register(Contract_type)
admin.site.register(Expense_point,ExpenseTimePointAdmin)