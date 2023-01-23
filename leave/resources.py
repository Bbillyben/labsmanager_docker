from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource
from .models import Leave, Leave_Type
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets
from import_export.fields import Field

from staff.models import Employee


class LeaveItemResources(labResource):
    first_name=Field(
        column_name=_('first_name'),
        attribute='employee', 
        widget=widgets.ForeignKeyWidget(Employee, 'first_name'), readonly=True,
    )  
    last_name=Field(
        column_name=_('last_name'),
        attribute='employee', 
        widget=widgets.ForeignKeyWidget(Employee, 'last_name'), readonly=True,
    ) 
    
    type=Field(
        column_name=_('type'),
        attribute='type', 
        widget=widgets.ForeignKeyWidget(Leave_Type, 'name'), readonly=False,
    )   
    class Meta:
        """Metaclass"""
        model = Leave
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id', ]
        export_order=['first_name', 
                      'last_name', 
                      'type',
                      'start_date',
                      'end_date',
                      'comment',
                      ]