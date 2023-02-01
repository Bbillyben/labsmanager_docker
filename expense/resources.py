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
from labsmanager.ressources import SimpleError, SkipErrorRessource
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




class ExpensePointResource(SkipErrorRessource):
    
    @classmethod
    def get_error_result_class(self):
        """
        Returns a class which has custom formatting of the error.
        """
        return SimpleError
    
    fund=FundField(
        column_name='Ref',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'ref')
        )
    type=Field(
        column_name='type',
        attribute='type',
        widget=ForeignKeyWidget(Cost_Type, 'short_name')
        )
    project=FundField(
        column_name='project',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'project__name')
        )
    institiution=FundField(
        column_name='institution',
        attribute='fund',
        widget=ForeignKeyWidget(Fund, 'institution__short_name')
        )
    amount=Field(
        column_name=_('expense'),
        attribute='amount', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    
    class Meta:
        model = Expense_point
        skip_unchanged = False
        report_skipped = True
        collect_failed_rows=False
        rollback_on_validation_errors=True
        use_transactions=True
        export_order  = ('project','institiution', 'fund','type', 'entry_date', 'value_date',  'amount', )