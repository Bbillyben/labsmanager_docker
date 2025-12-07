from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource, InfoWidget
from .models import Milestones
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets
from import_export.fields import Field

from labsmanager.ressources import percentageWidget, EmployeeListWidget

class MilestonesResource(labResource):
    class Meta:
        """Metaclass"""
        model = Milestones
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id','type',
         ]
        # export_order=['name',
        #               'start_date',
        #               'end_date',
        #               'institution',
        #               'leader',
        #               'participants',
        #               'Fund',
        #               'Total_fund',
        #               'Total_expense',
        #               'Total_Available',
        #               'Total_fund_focus',
        #               'Total_expense_focus',
        #               'Total_Available_focus',
        #               ]
    name=Field(
        column_name=_('Name'),
        attribute='name', 
        widget=widgets.CharWidget(), readonly=True
    )
    project=Field(
        column_name=_('Project'),
        attribute='project__name', 
        widget=widgets.CharWidget(), readonly=True
    )
    quotity=Field(
        column_name=_('Qutotity'),
        attribute='quotity', 
        widget=percentageWidget(max_num=1), readonly=True
    )
    employee=Field(
        column_name=_('Employees'),
        attribute='employee', 
        widget=EmployeeListWidget(), readonly=True
    )