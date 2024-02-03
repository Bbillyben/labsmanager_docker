from django.utils.translation import gettext as _
from django.db.models import Q
from labsmanager.ressources import labResource, SimpleError, SkipErrorRessource, DateField, percentageWidget, InfoWidget
from .models import Employee, Employee_Status, Team, TeamMate
from import_export.fields import Field
from labsmanager.utils import getDateFilter
import import_export.widgets as widgets

from django.contrib.auth.models import User   

class StatusWidget(widgets.CharWidget):
    
    param=None
    def __init__(self, param=''):
        super().__init__()
        self.param = param
        
    def render(self, value, obj=None):
        # print(str(value))
        v = value.filter(getDateFilter()).order_by('-end_date')
        if self.param is not None:
            v =v.values(self.param)
        else:
             v =v.values('pk')
        if v:
            strV = ', '.join(f'{key[self.param]}' for key in v)
            return strV 
        else:
            return "-"
class AllStatusWidget(widgets.CharWidget):
    
    param=[]
    def __init__(self, param=''):
        super().__init__()
        self.param = param
        
    def render(self, value, obj=None):
        # print(str(value))
        v = value.order_by('-end_date')
        v=v.values("type__shortname", "type__name", "start_date", "end_date")
        if v:
            strV = '\n '.join(f'{key["type__shortname"]} : {key["type__name"]} - {key["start_date"]} # {key["end_date"]}' for key in v)
            return strV 
        else:
            return "-"
          
class ContractWidget(widgets.CharWidget):
    def render(self, value, obj=None):
        
        v= value.filter(Q(is_active=True) & getDateFilter())
        li=[]
        for c in v:
            strC= str(c.fund.project.name) 
            strC+= " - " +str(c.fund.funder.name)
            strC+= " / " +str(c.fund.institution.short_name)
            strC+= " (" +str(c.start_date)
            strC+= "-" +str(c.end_date)+')'
            strC+= '#'+str(c.quotity)
            li.append(strC)
           
        return "\n".join(li)
    
class ProjectWidget(widgets.CharWidget):
    def render(self, value, obj=None):
        v= value.filter(Q(project__status=True)) # & getDateFilter())
        li=[]
        for c in v:
            strC= str(c.project.name) 
            strC+= " - " +str(c.status)
            strC+= " / " +str(c.quotity)
            strC+= " (" +str(c.start_date)
            strC+= " > " +str(c.end_date)+')'
            li.append(strC)
           
        return "\n".join(li)
    
class SuperiorWidget(widgets.CharWidget):
     def render(self, value, obj=None):
        li=[]
        for c in value:
            strC= str(c.superior.user_name) 
            li.append(strC)
           
        return ", ".join(li)
    
class EmployeeResource(labResource, SkipErrorRessource):
    first_name = Field(
        column_name=_('First Name'),
        attribute='first_name', 
        widget=widgets.CharWidget(), 
        readonly=True
        ) 
    last_name = Field(
        column_name=_('Last Name'),
        attribute='last_name', 
        widget=widgets.CharWidget(), 
        readonly=True
        ) 
    birth_date= DateField(
        column_name=_('Birth Date'),
        attribute='birth_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    entry_date= DateField(
        column_name=_('Entry Date'),
        attribute='entry_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    exit_date= DateField(
        column_name=_('Exit Date'),
        attribute='exit_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    
    status = Field(
        column_name=_('Status'),
        attribute='get_status', 
        widget=StatusWidget(param='type__name'), 
        readonly=True
        )
    status_startDate = Field(
        column_name=_('Status Start Date'),
        attribute='get_status', 
        widget=StatusWidget(param='start_date'), 
        readonly=True
        )
    status_endDate = Field(
        column_name=_('Status End Date'),
        attribute='get_status', 
        widget=StatusWidget(param='end_date'), 
        readonly=True
        ) 
    all_status = Field(
        column_name=_('All Status'),
        attribute='get_status', 
        widget=AllStatusWidget(), 
        readonly=True
        )
    info=Field(
        column_name=_('Infos'),
        attribute='info', 
        widget=InfoWidget(), 
        readonly=True
    )
    status_contract = Field(
        column_name=_('Status Contract Type'),
        attribute='get_status', 
        widget=StatusWidget(param='is_contractual'), 
        readonly=True
        ) 
    # contract = Field(
    #     column_name=_('Contracts'),
    #     attribute='contracts', 
    #     widget=ContractWidget(), 
    #     readonly=True
    #     )
    contracts_quotity = Field(
        column_name=_('contracts quotity'),
        attribute='contracts_quotity', 
        widget=percentageWidget(), 
        readonly=True
        )
    # project = Field(
    #     column_name=_('Projects'),
    #     attribute='projects', 
    #     widget=ProjectWidget(),
    #     readonly=True
    #     )  
    projects_quotity = Field(
        column_name=_('projects quotity'),
        attribute='projects_quotity', 
        widget=percentageWidget(), 
        readonly=True
        )    
    superior= Field(
        column_name=_('Superior'),
        attribute='get_current_superior', 
        widget=SuperiorWidget(), 
        readonly=True
        )    
    class Meta:
        """Metaclass"""
        model = Employee
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id',
                    'user',
         ]
  
class EmployeeAdminResource(labResource, SkipErrorRessource):
    first_name = Field(
        column_name=_('First Name'),
        attribute='first_name', 
        widget=widgets.CharWidget(), 
        readonly=False
        ) 
    last_name = Field(
        column_name=_('Last Name'),
        attribute='last_name', 
        widget=widgets.CharWidget(), 
        readonly=False
        ) 
    birth_date= DateField(
        column_name=_('Birth Date'),
        attribute='birth_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    entry_date= DateField(
        column_name=_('Entry Date'),
        attribute='entry_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    exit_date= DateField(
        column_name=_('Exit Date'),
        attribute='exit_date', 
        widget=widgets.DateWidget(), 
        readonly=False,
        ) 
    email = Field(
        column_name=_('Email'),
        attribute='email', 
        widget=widgets.CharWidget(), 
        readonly=False
        ) 
    user = Field(
        column_name=_('User'),
        attribute='user', 
        widget=widgets.ForeignKeyWidget(User, 'username'),
        readonly=True
        ) 
    
    
    def before_import_row(self, row, row_number=None, **kwargs):
        
        query = Q()
        first_name = row.get('First Name', None)
        if first_name is not None:
            query = query & Q(first_name__icontains=first_name)
        
        last_name = row.get('Last Name', None)
        if last_name is not None:
            query = query & Q(last_name__icontains=last_name)
        
        fu = Employee.objects.filter(query)
        if fu is not None and fu.count()==1:
            row["id"] = fu.first().pk
        else:
            row["id"] = None
        return fu
     
    class Meta:
        """Metaclass"""
        model = Employee
        skip_unchanged = True
        clean_model_instances = False
        exclude = [ ]
              
        
class TeamMateWidget(widgets.CharWidget):
    
    def render(self, value, obj=None):
        pa=TeamMate.objects.filter(team=value)
        
        li=[]
        for c in pa:
            strC= str(c.employee.user_name) 
            # strC+= " - " +str(c.get_status_display())
            # strC+= " (" +str(c.start_date)
            # strC+= " > " +str(c.end_date)+')'
            # strC+= '#'+str(c.quotity)
            li.append(strC)
           
        return "\n".join(li)       
class TeamResource(labResource):
    
    name = Field(
        column_name=_('Team Name'),
        attribute='name', 
        widget=widgets.CharWidget(), readonly=True
        ) 
    leader = Field(
        column_name=_('Leader'),
        attribute='leader__user_name', 
        widget=widgets.CharWidget(), readonly=True
        )
    mate = Field(
        column_name=_('Team Mate'),
        attribute='pk', 
        widget=TeamMateWidget(), readonly=True
        )
    class Meta:
        """Metaclass"""
        model = Team
        skip_unchanged = False
        clean_model_instances = False
        exclude = [ 'id',
            ]