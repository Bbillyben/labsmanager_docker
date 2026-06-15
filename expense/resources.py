from django.utils.translation import gettext as _
from django.db.models import Q
from django.core.exceptions import  ImproperlyConfigured, MultipleObjectsReturned
from labsmanager.ressources import labResource,  SimpleError, SkipErrorRessource, SkipSameValueRessource, DateField, DecimalField

from import_export.fields import Field

from labsmanager.utils import getDateFilter
from labsmanager.ressources import NormalizedDecimalField
import import_export.widgets as widgets
from import_export import resources, results

from fund.resources import FundField

from .models import Contract, Expense, Contract_expense
from expense.models import Expense_point
from fund.models import Fund, Cost_Type
from project.models import Project
from settings.models import LMProjectSetting


class CheckProjectTypeResourceMixin():
    class Meta:
        abstract=True
        valid_import=['s', 'e', 'h']
        
    def before_import_row(self, row, row_number=None, **kwargs):
        result = super().before_import_row(row, row_number, **kwargs)
        refI = row.get('Ref', None)
        if refI is not None:
            fu = Fund.objects.filter(ref=refI)
            if fu:
                project=fu.first().project
                
        if not project:
            project_name = row.get('project', None)
            if project_name is not None:
                projects = Project.objects.filter(name=project_name)
                if projects:
                    projects.first()
        if project:
            proj_set = LMProjectSetting.get_setting_object("EXPENSE_CALCULATION", project=project)
            if not proj_set.value in self._meta.valid_import:
                raise ImproperlyConfigured(_("The project %(proj)s is not configured to accept '%(imp_class)s' import (setting value : '%(set_val)s')")%({'proj':project.name, 'imp_class':self._meta.model.__name__, 'set_val':proj_set.as_choice()}))
        return result
    
class ExpenseResource(CheckProjectTypeResourceMixin, labResource, SkipSameValueRessource, SkipErrorRessource):
    expense_id=Field(
        column_name=_('Expense Id'),
        attribute='expense_id', 
    )
    type=Field(
        column_name=_('type'),
        attribute='type', 
        widget=widgets.ForeignKeyWidget(Cost_Type, 'short_name'), readonly=False
    )
    amount=NormalizedDecimalField(
        column_name=_('Amount'),
        attribute='amount', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    status = Field(
        column_name=_('Status'),
        attribute='get_status_display',
    )
    fund=FundField(
        column_name=_('Ref'),
        attribute='fund_item', 
        widget=widgets.ForeignKeyWidget(Fund, 'ref'), readonly=False
    )
    project=FundField(
        column_name=_('Project'),
        attribute='fund_item', 
        widget=widgets.ForeignKeyWidget(Fund, 'project__name'), readonly=True
    )
    funder=FundField(
        column_name=_('Funder'),
        attribute='fund_item', 
        widget=widgets.ForeignKeyWidget(Fund, 'funder__short_name'), readonly=True
    )
    institution=FundField(
        column_name=_('Institution'),
        attribute='fund_item', 
        widget=widgets.ForeignKeyWidget(Fund, 'institution__short_name'), readonly=True
    )
    desc=Field(
        column_name=_('Description'),
        attribute='desc', 
    )   
    
    class Meta:
        """Metaclass"""
        name=_("Single Expense Import")
        model = Expense
        skip_unchanged = False
        clean_model_instances = False
        exclude = [
                #    'id',
                   'fund_item',
         ]
        export_order  = ['expense_id', 'desc', 'type', 'amount', 'status', 
                         'project', 'fund', 'funder', 'institution',
            
        ]
        valid_import=['e', 'h']
        
    def before_import_row(self, row, row_number=None, **kwargs):
        super().before_import_row(row, row_number, **kwargs)
        qset = Expense.objects.none()
        if "id" in row and row["id"] != None:
            qset = Expense.objects.get(pk=row["id"])
        elif "Expense Id" in row and row["Expense Id"] != None:
            qset = Expense.objects.filter(expense_id=row["Expense Id"])
            if qset.count()==1:
                row["id"] = qset.first().pk
            # else:
            #     raise MultipleObjectsReturned(_("Expense id : '%(eid)s' return %(count)s objects for fund ref '%(fund)s'")%({'eid':row["Expense Id"], 'count':qset.count(), 'fund': row["Ref"]}))
        else:
            row["id"]=None
        return qset
        
    
    @classmethod
    def get_error_result_class(self):
        """
        Returns a class which has custom formatting of the error.
        """
        return SimpleError

class ContractResource(labResource):
    employee = Field(
        column_name=_('Employee'),
        attribute='employee__user_name', 
        widget=widgets.CharWidget(), readonly=True
        )
    project = Field(
        column_name=_('Project'),
        attribute='fund__project__name', 
        widget=widgets.CharWidget(), readonly=True
        )
    funder=Field(
        column_name=_('Funder'),
        attribute='fund__funder__name', 
        widget=widgets.CharWidget(), readonly=True
        )
    institution=Field(
        column_name=_('Institution'),
        attribute='fund__institution__short_name', 
        widget=widgets.CharWidget(), readonly=True
        )
    fund_ref=Field(
        column_name=_('fund ref'),
        attribute='fund__ref', 
        widget=widgets.CharWidget(), readonly=True
        )
    
    contract_type=Field(
        column_name=_('Contract type'),
        attribute='contract_type', 
        widget=widgets.CharWidget(), readonly=True
        )
    
    total_amount=Field(
        column_name=_('Total Amount'),
        attribute='total_amount', 
        widget=widgets.CharWidget(), readonly=True
        )
    class Meta:
        """Metaclass"""
        model = Contract
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id',
                   'fund',
                   ''
         ]

    
class ExpensePointResource(CheckProjectTypeResourceMixin, labResource, SkipErrorRessource):
    
    @classmethod
    def get_error_result_class(self):
        """
        Returns a class which has custom formatting of the error.
        """
        return SimpleError
    
    fund=FundField(
        column_name='Ref',
        attribute='fund',
        widget=widgets.ForeignKeyWidget(Fund, 'ref'),
        readonly=False
        )
    type=Field(
        column_name='type',
        attribute='type',
        widget=widgets.ForeignKeyWidget(Cost_Type, 'short_name'),
        readonly=False
        )
    project=FundField(
        column_name='project',
        attribute='fund',
        widget=widgets.ForeignKeyWidget(Fund, 'project__name'),
        readonly=True
        )
    institiution=FundField(
        column_name='institution',
        attribute='fund',
        widget=widgets.ForeignKeyWidget(Fund, 'institution__short_name'),
        readonly=True
        )
    amount=Field(
        column_name=_('expense'),
        attribute='amount', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    entry_date=DateField(
        column_name=_('Entry Date'),
        attribute='entry_date', 
        widget=widgets.DateWidget(),
        readonly=False
    )
    value_date=DateField(
        column_name=_('Value Date'),
        attribute='value_date',
        widget=widgets.DateWidget(),
        readonly=False
    )        
        
    def before_import_row(self, row, row_number=None, **kwargs):
        super().before_import_row(row, row_number, **kwargs)
        query = Q()
        project_name = row.get('project', None)
        if project_name is not None:
            query = query & Q(fund__project__name__icontains=project_name)
        
        refI = row.get('Ref', None)
        if refI is not None:
            query = query & Q(fund__ref=refI)
            
        typeC = row.get('type', None)
        if typeC is not None:
            query = query & Q(type__short_name=typeC)            
        
        
        fu = Expense_point.objects.filter(query)

        if fu is not None and fu.count()==1:
            row["id"] = fu.first().pk
        else:
            row["id"] = None
        return fu
    
    
    
    
    class Meta:
        name=_("Global Expense by type Import")
        model = Expense_point
        skip_unchanged = True
        clean_model_instances = False
        export_order  = ['project','institiution', 'fund','type', 'entry_date', 'value_date',  'amount', ]
        valid_import=['s', 'h']
        
        



class ConsolidatedExpenseResource(ExpenseResource):
    #class_type = Field(column_name=_("Class type"))
    
    contract_employee = Field(column_name=_("Contract employee"))
    contract_type = Field(column_name=_("Contract type"))
    contract_start_date = Field(column_name=_("Contract start date"))
    contract_end_date = Field(column_name=_("Contract end date"))
    # contract_status = Field(column_name=_("Contract status"))

    budget = Field(column_name=_("Budget"))
    # budget_name = Field(column_name=_("Budget name"))

    class Meta(ExpenseResource.Meta):
        model = Expense
        fields = (
            "date",
            "expense_id",
            "desc",
            "type",
            "amount",
            "status",
            "project",
            "fund",
            "funder",
            "institution",
            "budget",
            # "budget_name",
            #"class_type",
            "contract_employee",
            "contract_type",
            "contract_start_date",
            "contract_end_date",
            # "contract_status",
        )
        export_order = fields

    # def dehydrate_class_type(self, obj):
    #     return type(obj).__name__

    def dehydrate_budget(self, obj):
        if obj.budget_item:
            return str(obj.budget_item)
        return ""

    # def dehydrate_budget_name(self, obj):
    #     if obj.budget_item:
    #         return getattr(obj.budget_item, "name", str(obj.budget_item))
    #     return ""

    def get_contract(self, obj):
        if isinstance(obj, Contract_expense):
            return obj.contract
        return None

    def dehydrate_contract_employee(self, obj):
        contract = self.get_contract(obj)
        if contract:
            return str(contract.employee)
        return ""

    def dehydrate_contract_type(self, obj):
        contract = self.get_contract(obj)
        if contract:
            return str(contract.contract_type or "")
        return ""

    def dehydrate_contract_start_date(self, obj):
        contract = self.get_contract(obj)
        if contract:
            return contract.start_date
        return ""

    def dehydrate_contract_end_date(self, obj):
        contract = self.get_contract(obj)
        if contract:
            return contract.end_date
        return ""

    # def dehydrate_contract_status(self, obj):
    #     contract = self.get_contract(obj)
    #     if contract:
    #         return contract.get_status_display()
    #     return ""