from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource
from .models import Fund_Item, Fund, Cost_Type
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets
from import_export.fields import Field


        
        
class FundItemResource(labResource):
    available=Field(
        column_name=_('Total Available'),
        attribute='available', 
        widget=widgets.DecimalWidget(), readonly=True
    )
    type=Field(
        column_name=_('type'),
        attribute='type', 
        widget=widgets.ForeignKeyWidget(Cost_Type, 'name'), readonly=True
    )
    project=Field(
        column_name=_('Project'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'project__name'), readonly=True
    )
    funder=Field(
        column_name=_('funder'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'funder__short_name'), readonly=True
    )
    institution=Field(
        column_name=_('institution'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'institution__short_name'), readonly=True
    )
    start_date=Field(
        column_name=_('Start Date'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'start_date'), readonly=False
    )
    end_date=Field(
        column_name=_('End Date'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'end_date'), readonly=False
    )
    fund=Field(
        column_name=_('Ref'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'ref'), readonly=True
    )
    
    class Meta:
        """Metaclass"""
        model = Fund_Item
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id','fund' ]
        export_order=['project', 
                      'funder',
                      'institution',
                      'start_date',
                      'end_date',
                      'type',
                      'fund',
                      'amount',
                      'expense',
                      'available',
                      ]
        

class FundItemField(Field):
     def clean(self, data, **kwargs):
        print("---------- [FundItemField] ----------------")
        print(str(self.column_name))
        # print(" data :" + str(data))
        # print(" kwargs :" + str(kwargs))
        # print("---------- ----------------")
        return super().clean(data, **kwargs)

class FundField(Field):
     def clean(self, data, **kwargs):
        print("---------- [FundField] ----------------")
        print(str(self.column_name))
        # print(" data :" + str(data))
        # print(" kwargs :" + str(kwargs))
        # print("---------- ----------------")
        query = Q(amount__gte=-1)
        project_name = data.get('Project', None)
        if project_name is not None:
            query = query & Q(project__name__icontains=project_name)
        
        funder_name = data.get('funder', None)
        if project_name is not None:
            query = query & (Q(funder__name__icontains=funder_name) | Q(funder__short_name__icontains=funder_name))
        
        inst_name = data.get('institution', None)
        if inst_name is not None:
            query = query & (Q(institution__name__icontains=inst_name) | Q(institution__short_name__icontains=inst_name))
        
        refI = data.get('Ref', None)
        if refI is not None:
            query = query & Q(ref=refI)
        
        fu = Fund.objects.filter(query).first()
        return fu
   
    
class FundItemAdminResource(labResource):
    fund=FundField(
        column_name=_('Ref'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'ref'), 
        readonly=False
    )
    type=Field(
        column_name=_('type'),
        attribute='type', 
        widget=widgets.ForeignKeyWidget(Cost_Type, 'short_name'), 
        readonly=False
    )
    project=FundField(
        column_name=_('Project'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'project__name'),
        readonly=False
    )
    funder=FundField(
        column_name=_('funder'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'funder__short_name'), 
        readonly=False
    )
    institution=FundField(
        column_name=_('institution'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'institution__short_name'), 
        readonly=False
    )
    start_date=FundField(
        column_name=_('Start Date'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'start_date'), 
        readonly=False
    )
    end_date=FundField(
        column_name=_('End Date'),
        attribute='fund', 
        widget=widgets.ForeignKeyWidget(Fund, 'end_date'),
        readonly=False
    )
    
    amount=FundItemField(
        column_name=_('amount'),
        attribute='amount', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    expense=FundItemField(
        column_name=_('expense'),
        attribute='expense', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    available=FundItemField(
        column_name=_('available'),
        attribute='available', 
        widget=widgets.DecimalWidget(),
        readonly=False
    )
    
    def get_or_init_instance(self, instance_loader, row):
        print(">>>>>>>>>>> get_or_init_instance <<<<<<<<<<<<<<<<<<< ")
        print(str(instance_loader))
        print(str(instance_loader.resource))
        print(row)
        
        return super().get_or_init_instance(instance_loader, row)
    
    def before_import_row(self, row, row_number=None, **kwargs):
        print(">>>>>>>>>>> before_import_row <<<<<<<<<<<<<<<<<<< ")
        # print(" row :"+str(row))
        # print(" row_number :"+str(row_number))
        # print(" kwargs :"+str(kwargs))
        query = Q(amount__gte=-1)
        project_name = row.get('Project', None)
        if project_name is not None:
            query = query & Q(fund__project__name__icontains=project_name)
        
        funder_name = row.get('funder', None)
        if project_name is not None:
            query = query & (Q(fund__funder__name__icontains=funder_name) | Q(fund__funder__short_name__icontains=funder_name))
        
        inst_name = row.get('institution', None)
        if inst_name is not None:
            query = query & (Q(fund__institution__name__icontains=inst_name) | Q(fund__institution__short_name__icontains=inst_name))
        
        refI = row.get('Ref', None)
        if refI is not None:
            query = query & Q(fund__ref=refI)
            
        typeC = row.get('type', None)
        if typeC is not None:
            query = query & Q(type__short_name__icontains=typeC)            
        
        fu = Fund_Item.objects.filter(query).first()
        if fu:
            row["id"] = fu.pk
        return fu
        
    class Meta:
        """Metaclass"""
        model = Fund_Item
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ '' ]
        #import_id_fields=('fund', 'type')
        export_order=['project', 
                      'funder',
                      'institution',
                      'start_date',
                      'end_date',
                      'type',
                      'fund',
                      'amount',
                      'expense',
                      'available',
                      ]