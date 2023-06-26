from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource
from .models import Leave, Leave_Type
from staff.models import Employee
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets
from import_export.fields import Field

from staff.models import Employee


from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget, CharWidget
from import_export import resources, results
from import_export.instance_loaders import BaseInstanceLoader
from labsmanager.ressources import SimpleError

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
        skip_unchanged = True
        clean_model_instances = False
        exclude = [ 'id', 'employee', ]
        export_order=[
                      'first_name', 
                      'last_name', 
                      'type',
                      'start_date',
                      'start_period',
                      'end_date',
                      'end_period',
                      'comment',
                      ]

from django.db.models import Q, F, ExpressionWrapper, fields, Value
from django.db.models.functions import Cast, Coalesce, Now, Extract, Abs, Concat
class EmployeeLeaveField(Field):
    
    def clean(self, data, **kwargs):
        userName =data.get('Employee', None)
        if userName is None:
            return None
        allEmp=Employee.objects.all().annotate(username=Concat(F('first_name'), Value(" "),F('last_name')))
        emp=allEmp.filter(username__icontains = userName).first()
        return emp
        
class LeaveItemAdminResources(labResource):
    # @classmethod
    # def get_error_result_class(self):
    #     """
    #     Returns a class which has custom formatting of the error.
    #     """
    #     return SimpleError
    
    
    type=Field(
        column_name=_('type'),
        attribute='type', 
        widget=ForeignKeyWidget(Leave_Type, 'name'), 
        readonly=False,
    )   
    employee=EmployeeLeaveField(
        column_name=_('Employee'),
        attribute='employee', 
        widget=ForeignKeyWidget(Employee, 'user_name'), #(Employee, 'user_name'), 
        readonly=False,
    )   
    class Meta:
        """Metaclass"""
        model = Leave
        skip_unchanged = True
        report_skipped = True
        collect_failed_rows=True
        rollback_on_validation_errors=True
        use_transactions=True
        clean_model_instances = False
        # exclude = [ 'employee', ]
        export_order=[
                      'employee', 
                      'type',
                      'start_date',
                      'start_period',
                      'end_date',
                      'end_period',
                      'comment',
                      ]
