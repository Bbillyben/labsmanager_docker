from multiprocessing import context
from django.contrib.auth.models import User, Group
from rest_framework import serializers
from staff.models import Employee, Employee_Status, Employee_Superior, Employee_Type, Team, TeamMate, GenericInfo, GenericInfoType
from expense.models import Expense_point, Contract, Contract_expense, Contract_type
from fund.models import Fund, Cost_Type, Fund_Item, Fund_Institution, Budget, Contribution
from project.models import Project, Institution, Participant,Institution_Participant, GenericInfoProject, GenericInfoTypeProject
from endpoints.models import Milestones
from leave.models import Leave, Leave_Type
from common.models import  favorite
from django.db.models import Sum, Count


from datetime import timedelta, datetime


 # User and Group Serailizer ########### ------------------------------------ ###########
       
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['pk','username', 'first_name','last_name', 'email', 'groups', 'is_active',]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['pk', 'url', 'name']
        


# ------------------------------------------------------------------------------------ #
# ---------------------------    MINIMALIST SERIALISZER    --------------------------- #
# ------------------------------------------------------------------------------------ #

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP PROJECT 

class InstitutionSerializer(serializers.ModelSerializer):
     class Meta:
        model = Institution
        fields = ['pk', 'short_name', 'name', 'adress',]  
        

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['pk', 'name', 'start_date', 'start_date', 'end_date', 'status']


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP FUND 

class CostTypeSerialize(serializers.ModelSerializer):
     class Meta:
        model = Cost_Type
        fields = ['pk', 'short_name', 'name', 'in_focus',] 
        
class CostTypeSerialize_tree(serializers.ModelSerializer):
    ancestors_count=serializers.SerializerMethodField()
    class Meta:
        model = Cost_Type
        fields = ['pk', 'short_name', 'name', 'in_focus', 'ancestors_count',] 
        
    def get_ancestors_count(self,obj):
        return obj.get_ancestors(ascending=False, include_self=False).count()
        
class Fund_InstitutionSerializer(serializers.ModelSerializer):
     class Meta:
        model = Fund_Institution
        fields = ['pk', 'short_name', 'name',]  

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Employee 

class EmployeeTypeSerialize(serializers.ModelSerializer):
    class Meta:
        model = Employee_Type
        fields = ['pk', 'shortname', 'name', ]

        
class EmployeeSerialize_Min(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    
    class Meta:
        model = Employee
        fields = ['pk', 'user_name', 'is_active']    
 
 
class UserEmployeeSerializer(serializers.ModelSerializer):
    employee=serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['pk','username', 'first_name','last_name','employee'] 
    
    def get_employee(self,obj):
        try:
            emp = Employee.objects.get(user=obj)
            return EmployeeSerialize_Min(emp, many=False).data    
        except:
            return None

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Expense

class ContractTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract_type
        fields = ['pk', 'name',]  

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Endpoint
class MilestonesSerializer(serializers.ModelSerializer):
    project=ProjectSerializer(many=False, read_only=True)
    class Meta:
        model = Milestones
        fields = ['pk', 'name', 'deadline_date', 'quotity', 'status', 'desc', 'type', 'get_type_display', 'project']  


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Leave
class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leave_Type
        fields = ['pk', 'short_name', 'name', 'parent','color',]  
        
class LeaveTypeSerializer_tree(serializers.ModelSerializer):
    ancestors_count=serializers.SerializerMethodField()
    
    class Meta:
        model = Leave_Type
        fields = ['pk', 'short_name', 'name', 'parent','color', 'ancestors_count']  
        
    def get_ancestors_count(self,obj):
        return obj.get_ancestors(ascending=False, include_self=False).count()
        
        
class LeaveSerializerBasic(serializers.ModelSerializer):
    class Meta:
        model = Leave
        fields = ['pk', 'employee', 'type', 'start_date','start_period', 'end_date','end_period',] 
        
class LeaveSerializer(serializers.ModelSerializer):
    employee=EmployeeSerialize_Min(many=False, read_only=True)
    type=LeaveTypeSerializer(many=False, read_only=True)
    class Meta:
        model = Leave
        fields = ['pk', 'employee', 'type', 'start_date','start_period', 'end_date','end_period',]  

class LeaveSerializer1D(serializers.ModelSerializer):
    employee = serializers.CharField(source='employee.user_name')
    employee_pk = serializers.CharField(source='employee.pk')
    type = serializers.CharField(source='type.name')
    type_pk = serializers.CharField(source='type.pk')
    start= serializers.DateField(source='start_date')
    end=serializers.DateField(source='end_date')
    title=serializers.SerializerMethodField()
    color= serializers.CharField(source='type.color')
    days= serializers.CharField(source='dayCount')
    start_period_di=serializers.SerializerMethodField()
    end_period_di=serializers.SerializerMethodField()
    
    class Meta:
        model = Leave
        fields = ['pk', 'employee', 'employee_pk', 'type', 'type_pk', 'start','start_period_di', 'end', 'end_period_di','title', 'color', 'comment', 'days']  
        
    def get_title(self,obj):
        return f'{obj.type.name} - {obj.employee.user_name}'
    
    def get_start_period_di(self,obj):
        return obj.get_start_period_display()
    def get_end_period_di(self,obj):
        return obj.get_end_period_display()
    
class LeaveSerializer1DCal(LeaveSerializer1D):
    end=serializers.SerializerMethodField()
    resourceId= serializers.CharField(source='employee.pk')
    start_period_di=serializers.SerializerMethodField()
    end_period_di=serializers.SerializerMethodField()
    start=serializers.SerializerMethodField()
    end=serializers.SerializerMethodField()
    
    class Meta:
        model = Leave
        fields = ['pk', 'employee', 'employee_pk', 'type', 'type_pk', 'start', 'start_period_di', 'end', 'end_period_di', 'title', 'color', 'comment','resourceId',]  
    
    def get_start(self,obj):
        st= obj.start_date.isoformat()
        if obj.start_period == "MI":
            st = st +" 12:00"
        return st
    
    def get_end(self,obj):
        ed=datetime.combine(obj.end_date ,datetime.min.time())
        ed = ed +timedelta(days=1)
        if obj.end_period == "MI":
            ed = ed + timedelta(hours=-12)
        return ed
    
    
    
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    For calendar 
class EmployeeSerialize_Cal(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    id = serializers.CharField(source='pk')
    title = serializers.CharField(source='user_name')
    class Meta:
        model = Employee
        fields = ['id', 'title', ]  
        
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Common
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.apps import apps

class ContentTypeSerialize(serializers.ModelSerializer):
    modelname=serializers.SerializerMethodField()
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model', 'modelname',] 
        
    def get_modelname(self,obj):
        return apps.get_model(obj.app_label, obj.model)._meta.verbose_name.title()
    
class FavoriteSerialize(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    content_type=ContentTypeSerialize(many=False, read_only=True)
    object_name=serializers.SerializerMethodField()
    object_url=serializers.SerializerMethodField()
    class Meta:
        model = favorite
        fields = ['pk', 'user', 'content_type', 'object_id', 'object_name','object_url',] 
        
    def get_object_name(self,obj):
        return obj.content_object.__str__()
    
    def get_object_url(self,obj):
        if obj.content_type.model == 'project':
            return reverse('project_single', args=[obj.object_id])
        if obj.content_type.model == 'employee':
            return reverse('employee', args=[obj.object_id])
        if obj.content_type.model == 'team':
            return reverse('team_single', args=[obj.object_id])

        return "-"
    
# --------------------------------------------------------------------------------------- #
# ---------------------------    APP PROJECT / SERIALISZER    --------------------------- #
# --------------------------------------------------------------------------------------- #


  
class Institution_ProjectParticipantSerializer(serializers.ModelSerializer):
    institution=InstitutionSerializer(many=False, read_only=True)
    status_name=serializers.CharField(source='get_status_display')
    
    class Meta:
        model = Institution_Participant
        fields = ['pk', 'institution','status', 'status_name'] 
               
class Institution_ParticipantSerializer(serializers.ModelSerializer):
    project=ProjectSerializer(many=False, read_only=True)
    institution=InstitutionSerializer(many=False, read_only=True)
    
    class Meta:
        model = Institution_Participant
        fields = ['pk', 'project', 'institution', 'status']  

class ParticipantSerializer(serializers.ModelSerializer):
    status=serializers.SerializerMethodField()
    project=ProjectSerializer(many=False, read_only=True)
    # project_name=serializers.SerializerMethodField()
    # project_status=serializers.SerializerMethodField()
    # project_start_date=serializers.SerializerMethodField()
    # project_end_date=serializers.SerializerMethodField()
    # project_pk=serializers.SerializerMethodField()
    class Meta:
        model = Participant
        # fields = ['pk', 'project_pk', 'project_name', 'project_start_date', 'project_end_date', 'project_status', 'status', 'quotity' ]
        fields = ['pk', 'project', 'start_date', 'end_date', 'status', 'quotity' ]
    
    def get_status(self,obj):
        return obj.get_status_display()
    
    def get_project_name(self,obj):
        return obj.project.name
    
    def get_project_start_date(self,obj):
        return obj.project.start_date
    
    def get_project_end_date(self,obj):
        return obj.project.end_date
        
    def get_project_status(self,obj):
        return obj.project.status
    
    def get_project_pk(self,obj):
        return obj.project.pk
    
class TeamParticipantSerializer(ParticipantSerializer):
    participant = serializers.SerializerMethodField() 
    class Meta:
        model = Participant
        # fields = ['pk', 'project_pk', 'project_name', 'project_start_date', 'project_end_date', 'project_status', 'status', 'quotity' ]
        fields = ['pk', 'project', 'start_date', 'end_date', 'status', 'quotity', 'participant', ]
    
    def get_participant(self,obj):
        part = Participant.objects.select_related('employee').filter(project = obj.project.pk, employee__is_active= True)
        return ParticipantProjectSerializer(part , many=True).data

# ------------------------------------------------------------------------------------ #
# ---------------------------    APP FUND / SERIALISZER    --------------------------- #
# ------------------------------------------------------------------------------------ #


class FundSerialize(serializers.ModelSerializer):
    funder=Fund_InstitutionSerializer(many=False, read_only=True)
    institution=InstitutionSerializer(many=False, read_only=True)
    project=ProjectSerializer(many=False, read_only=True)
    class Meta:
        model = Fund
        fields = ['pk', 'project', 'funder', 'institution', 'ref','start_date', 'end_date',
                  'is_active','amount', 'expense', 'available', 'amount_f', 'expense_f', 'available_f',]          

class FundConsumptionSerialize(serializers.ModelSerializer):
    funder=Fund_InstitutionSerializer(many=False, read_only=True)
    institution=InstitutionSerializer(many=False, read_only=True)
    project=ProjectSerializer(many=False, read_only=True)
    ratio=serializers.SerializerMethodField()
    time_ratio=serializers.SerializerMethodField()
    class Meta:
        model = Fund
        fields = ['pk', 'project', 'funder', 'institution', 'ref','start_date', 'end_date', 'is_active',
                  'amount', 'expense','available',
                  'amount_f', 'expense_f', 'available_f',
                  'ratio', 'time_ratio',] 
    
    def get_ratio(self,obj):
        if obj.amount  and int(obj.amount)>0:
            return abs(obj.expense/obj.amount)
        return '-'
    
    def get_time_ratio(self,obj):
        if not obj.amount  or  int(obj.amount)<=0:
            return '-'
        try:
            sd = obj.start_date
            se = obj.end_date
            sn = datetime.now().date()   
            d1=sn-sd
            d2=se-sd
            r = min((d1.days)/(d2.days), 1)
            #r = abs(float(obj.expense)/(float(obj.amount) * rd ))
        except:
            r = "-"
        return r
    
class FundItemSerialize(serializers.ModelSerializer):
    fund=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Fund_Item
        fields = ['pk', 'type', 'fund','amount',  'expense','available','value_date', 'entry_date',]   
        
class FundItemSerializePlus(serializers.ModelSerializer):
    fund=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    contract=serializers.SerializerMethodField()
    class Meta:
        model = Fund_Item
        fields = ['pk', 'type', 'fund','amount',  'expense','available','value_date', 'entry_date',
                  'contract',] 
            
    def get_contract(self,obj):
        from expense.models import Contract
        ct = Contract.objects.filter(fund = obj.fund, is_active = True)
        return ContractSerializerSimple(ct, many=True).data

class FundItemSerialize_min(serializers.ModelSerializer):
    type=CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Fund_Item
        fields = ['pk', 'type', 'amount','expense','value_date', 'entry_date',]  
        
class FundStaleSerializer(serializers.ModelSerializer):
    availability=serializers.SerializerMethodField()
    project=ProjectSerializer(many=False, read_only=True)
    funder=serializers.SerializerMethodField()
    institution=serializers.SerializerMethodField()
    
    class Meta:
        model = Fund
        fields=['pk', 'project', 'funder', 'institution', 'end_date', 'availability', 
                'amount','expense','available',
                'amount_f', 'expense_f', 'available_f',
                ]
        
    def get_availability(self,obj):
        # avail=obj.get_available()
        # return avail['amount'].sum(axis=0, skipna=True)
        return obj.amount + obj.expense
    def get_project(self,obj):
        return obj.project.name
    def get_funder(self, obj):
        return obj.funder.short_name
    def get_institution(self, obj):
        return obj.institution.short_name
    
    
class FundProjectSerialize(serializers.ModelSerializer):
    funder=Fund_InstitutionSerializer(many=False, read_only=True)
    institution=InstitutionSerializer(many=False, read_only=True)
    #amount =serializers.SerializerMethodField()
    
    class Meta:
        model = Fund
        fields = ['pk', 'funder', 'institution', 'start_date', 'end_date', 'ref', 
                  'amount', 'is_active', 'expense', 'available',
                   'amount_f', 'expense_f', 'available_f',
                   ] 
        
    # def get_amount(self,obj):
    #     return Fund_Item.objects.filter(fund=obj.pk).aggregate(Sum('amount'))["amount__sum"]

class ExpensePOintSerializer(serializers.ModelSerializer):
    fund=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Expense_point
        fields = ['pk', 'entry_date', 'value_date', 'fund', 'type', 'amount']
        
        
# ---------------------------------------------------------------------------------------- #
# ---------------------------    APP Expense / SERIALISZER    --------------------------- #
# ---------------------------------------------------------------------------------------- #
 
class ContractSerializer(serializers.ModelSerializer):
    fund = FundSerialize(many=False, read_only=True)
    contract_type = serializers.SerializerMethodField()
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    class Meta:
        model = Contract
        fields = ['pk', 'employee', 'start_date', 'end_date', 'fund', 'contract_type','total_amount', 'quotity', 'is_active',]
    
    def get_contract_type(self,obj):
        if obj.contract_type:
            return obj.contract_type.name
        return None 

class ContractSerializerSimple(serializers.ModelSerializer):
    contract_type = serializers.SerializerMethodField()
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    class Meta:
        model = Contract
        fields = ['pk', 'employee', 'start_date', 'end_date','contract_type','total_amount', 'quotity', 'is_active',]
    
    def get_contract_type(self,obj):
        if obj.contract_type:
            return obj.contract_type.name
        return None     
          
class ContractExpenseSerializer_min(serializers.ModelSerializer):
    fund = FundSerialize(many=False, read_only=True)
    status = serializers.SerializerMethodField()
    type =   CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Contract_expense
        fields = ['pk', 'date', 'type', 'status', 'fund', 'amount']
        
    def get_status(self,obj):
        return obj.get_status_display()
    
# class ContractSerializer(serializers.ModelSerializer):
#     expenses = ContractExpenseSerializer_min(many=True, read_only=True)
#     employee=EmployeeSerialize_Min(many=False, read_only=True)
#     fund=FundSerialize(many=False, read_only=True)
#     class Meta:
#         model = Contract
#         fields = ['pk', 'employee', 'start_date', 'end_date', 'quotity',  'fund',
#                   'total_amount',
#                   'expenses', ]
    
# ---------------------------------------------------------------------------------------- #
# ---------------------------    APP EMPLOYEE / SERIALISZER    --------------------------- #
# ---------------------------------------------------------------------------------------- #
        
class EmployeeInfoTypeSerialize(serializers.ModelSerializer):
    class Meta:
        model = GenericInfoType
        fields = ['pk', 'name', 'icon', ]

from faicon.widgets import parse_icon

class EmployeeInfoTypeIconSerialize(serializers.ModelSerializer):
    icon_val=serializers.SerializerMethodField()
    class Meta:
        model = GenericInfoType
        fields = ['pk', 'name', 'icon_val', ]
        
    def get_icon_val(self,obj):
        ic =parse_icon(str(obj.icon))
        return {'style':ic.style, "icon":ic.icon}
    
        
class EmployeeInfoSerialize(serializers.ModelSerializer):
    info = EmployeeInfoTypeSerialize(many=False, read_only=True)
    class Meta:
        model = GenericInfo
        fields = ['pk', 'info', 'value', ]
    
class EmployeeStatusSerialize(serializers.ModelSerializer):
    type = EmployeeTypeSerialize(many=False, read_only=True)
    is_contractual=serializers.SerializerMethodField()
    class Meta:
        model = Employee_Status
        fields = ['pk', 'type', 'start_date', 'end_date', 'is_contractual', 'is_active',]
        
    def get_is_contractual(self,obj):
        return obj.get_is_contractual_display()

class EmployeeSuperiorSerialize(serializers.ModelSerializer):
    employee_superior=EmployeeSerialize_Min(many=False, read_only=True, source='superior')
    class Meta:
        model = Employee_Superior
        fields = ['pk', 'employee','employee_superior', 'start_date', 'end_date', 
                  'is_active',]
        
        
from django.http import JsonResponse       
class EmployeeOrganizationChartSerialize(serializers.ModelSerializer):
    status = EmployeeStatusSerialize(many=True, read_only=True, source='get_status')
    subordinate = serializers.SerializerMethodField()
    subordinate_count = serializers.SerializerMethodField()

   
    class Meta:
        model = Employee
        fields = ['pk', 'user_name','status','subordinate_count', 'subordinate', ]
    
    def get_subordinate(self,obj):
        sub = obj.get_current_subordinate()
        emp=Employee.objects.filter(pk__in=sub.values('employee'))
        return EmployeeOrganizationChartSerialize(emp,many=True).data
        
    def get_subordinate_count(self,obj):
        sub = obj.get_current_subordinate()
        return sub.count()
     
class EmployeeSerialize(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    get_status =EmployeeStatusSerialize(many=True, read_only=True)
    # contracts=ContractSerializer(many=True, read_only=True)
    # projects=ParticipantSerializer(many=True, read_only=True)
    info=EmployeeInfoSerialize(many=True, read_only=True)
    superior=EmployeeSuperiorSerialize(many=True, read_only=True, source='get_current_superior')
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Employee
        fields = ['pk','first_name', 'last_name', 'user', 'birth_date', 'entry_date', 'exit_date','email',
                  'is_team_leader','is_team_mate','get_status','is_active',
                  'contracts_quotity',
                  'projects_quotity',
                  'info',
                  'superior',
                  'has_perm',
                  ]
        
class TeamMateSerializer_min(serializers.ModelSerializer):
    employee=EmployeeSerialize_Min(many=False, read_only=True)
    class Meta:
        model = TeamMate
        fields=['pk', 'employee', 'start_date', 'end_date', 'is_active',]
    
    
class TeamSerializer(serializers.ModelSerializer):
    leader=EmployeeSerialize_Min(many=False, read_only=True)
    team_mate=TeamMateSerializer_min(many=True, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    
    class Meta:
        model= Team
        fields=['pk','name', 'leader', 'team_mate', 'has_perm']



class ParticipantProjectSerializer(serializers.ModelSerializer):
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    status_name=serializers.SerializerMethodField()
    class Meta:
        model = Participant
        fields = ['pk', 'employee', 'start_date', 'end_date', 'status', 'status_name', 'quotity' ]
    
    def get_status_name(self,obj):
        return obj.get_status_display()



#  For Team table
class TeamProjectSerializer(serializers.ModelSerializer):
    fund=serializers.SerializerMethodField() 
    participant = serializers.SerializerMethodField() 
    institution=serializers.SerializerMethodField()
    class Meta:
        model = Project
        fields = ['pk', 'name', 'start_date', 'end_date', 'status', 
                  'participant',
                  'institution', 
                  'fund',
                  ]
    def get_fund(self,obj):
        fund = Fund.objects.select_related('funder', 'institution').filter(project = obj.pk)
        return FundProjectSerialize(fund , many=True).data
    def get_participant(self,obj):
        part = Participant.objects.select_related('employee').filter(project = obj.pk, employee__is_active= True)
        return ParticipantProjectSerializer(part , many=True).data
    def get_institution(self,obj):
        ip = Institution_Participant.objects.filter(project = obj.pk)
        return Institution_ProjectParticipantSerializer(ip , many=True).data
    
    
    
#  For project table
       
class ProjectInfoTypeSerialize(serializers.ModelSerializer):
    class Meta:
        model = GenericInfoTypeProject
        fields = ['pk', 'name', 'icon', ] 

class ProjectInfoTypeIconSerialize(serializers.ModelSerializer):
    icon_val=serializers.SerializerMethodField()
    class Meta:
        model = GenericInfoTypeProject
        fields = ['pk', 'name', 'icon_val', ]
        
    def get_icon_val(self,obj):
        ic =parse_icon(str(obj.icon))
        return {'style':ic.style, "icon":ic.icon}    
    
       
class ProjectInfoSerialize(serializers.ModelSerializer):
    info = ProjectInfoTypeSerialize(many=False, read_only=True)
    class Meta:
        model = GenericInfoProject
        fields = ['pk', 'info', 'value', ]

class ProjectFullSerializer(serializers.ModelSerializer):
    participant = serializers.SerializerMethodField() 
    participant_count=serializers.SerializerMethodField()
    fund=serializers.SerializerMethodField() 
    institution=serializers.SerializerMethodField()
    # total_amount= serializers.SerializerMethodField()
    info=ProjectInfoSerialize(many=True, read_only=True)
    
    
    class Meta:
        model = Project
        fields = ['pk', 'name', 'start_date', 'end_date', 'status', 
                  'participant', 'participant_count',
                  'institution', 
                  'fund','get_funds_amount', 'get_funds_expense','get_funds_available',
                  'get_funds_amount_f', 'get_funds_expense_f','get_funds_available_f',
                  'info',
                  ]
    def get_participant(self,obj):
        part = Participant.objects.select_related('employee').filter(project = obj.pk, employee__is_active= True)
        return ParticipantProjectSerializer(part , many=True).data
    
    def get_participant_count(self,obj):
        part = Participant.objects.filter(project = obj.pk, employee__is_active= True).count()
        return part
    
    def get_fund(self,obj):
        fund = Fund.objects.select_related('funder', 'institution').filter(project = obj.pk)
        return FundProjectSerialize(fund , many=True).data
    
    def get_institution(self,obj):
        ip = Institution_Participant.objects.filter(project = obj.pk)
        return Institution_ProjectParticipantSerializer(ip , many=True).data
    
    # def get_total_amount(self,obj):
    #     fund = Fund.objects.filter(project = obj.pk)
    #     return Fund_Item.objects.filter(fund__in=fund).aggregate(Sum('amount'))["amount__sum"]
    
    
    
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Budget
class BudgetSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    cost_type=CostTypeSerialize(many=False, read_only=False)
    fund=FundSerialize(many=False, read_only=False)
    emp_type=EmployeeTypeSerialize(many=False, read_only=False)
    employee=EmployeeSerialize_Min(many=False, read_only=False)
    contract_type=ContractTypeSerializer(many=True, read_only=True)
    class Meta:
        model = Budget
        fields = ['pk', 'cost_type', 'fund', 'emp_type', 'employee', 'quotity', 'amount','contract_type', 'desc',]  
    
class ContribSerializer(BudgetSerializer):
    # user = UserSerializer(many=False, read_only=True)
    cost_type=CostTypeSerialize(many=False, read_only=False)
    fund=FundSerialize(many=False, read_only=False)
    emp_type=EmployeeTypeSerialize(many=False, read_only=False)
    employee=EmployeeSerialize_Min(many=False, read_only=False)
    contract_type=ContractTypeSerializer(many=True, read_only=True)
    class Meta:
        model = Contribution
        fields = ['pk', 'cost_type', 'fund', 'emp_type', 'employee', 'quotity', 'amount','contract_type','desc',
                  'start_date', 'end_date', 'is_active'] 