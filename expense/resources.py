from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource
from .models import Contract
from expense.models import Expense_point
from fund.models import Fund, Cost_Type
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets

from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from import_export import resources, results

from labsmanager.ressources import SimpleError, SkipErrorRessource, DateField
from fund.resources import FundField

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

    
class ExpensePointResource(labResource, SkipErrorRessource):
    
    @classmethod
    def get_error_result_class(self):
        """
        Returns a class which has custom formatting of the error.
        """
        return SimpleError
    
    fund=FundField(
        column_name='Ref',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'ref'),
        readonly=True
        )
    type=Field(
        column_name='type',
        attribute='type',
        widget=ForeignKeyWidget(Cost_Type, 'short_name'),
        readonly=True
        )
    project=FundField(
        column_name='project',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'project__name'),
        readonly=True
        )
    institiution=FundField(
        column_name='institution',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'institution__short_name'),
        readonly=True
        )
    amount=Field(
        column_name=_('expense'),
        attribute='amount', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    entry_date=DateField(
        column_name=_('entry_date'),
        attribute='entry_date', 
        widget=widgets.DateWidget(),
        readonly=False
    )
    value_date=DateField(
        column_name=_('value_date'),
        attribute='value_date',
        widget=widgets.DateWidget(),
        readonly=False
    )
    
    # def skip_row(self, instance, original, row, import_validation_errors=None):
    #     print("------------ skip_row")
    #     print("  - instance :"+str(instance))
    #     print("  - original :"+str(original))
    #     print("  - row :"+str(row))
    #     print("  - import_validation_errors :"+str(import_validation_errors))
        
    #     for field in self.get_import_fields():
    #         print("  - field :"+str(field))
    #         print("     -> field.get_value(instance) :"+str(field.get_value(instance)))
    #         print("     -> field.get_value(instance) :"+str(field.get_value(original)))
    #     return super().skip_row(instance, original, row, import_validation_errors)
        
        
    def before_import_row(self, row, row_number=None, **kwargs):
        
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
        model = Expense_point
        skip_unchanged = True
        clean_model_instances = False
        export_order  = ['project','institiution', 'fund','type', 'entry_date', 'value_date',  'amount', ]