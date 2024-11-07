from multiprocessing import context
from django.contrib.auth.models import User, Group
from rest_framework import serializers
from staff.models import Employee, Employee_Status, Employee_Superior, Employee_Type, Team, TeamMate, GenericInfo, GenericInfoType
from expense.models import Expense_point, Contract, Contract_expense, Contract_type, Expense
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
        fields = ['pk', 'short_name', 'name',]  
        

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
        fields = ['pk', 'short_name', 'name', 'in_focus', 'is_hr', 'ancestors_count',] 
        
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
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    class Meta:
        model = User
        fields = ['pk','username', 'first_name','last_name', 'last_login', 'employee',
                  'is_staff','is_superuser','is_active',
                  'groups',
                  ] 
    
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
    has_perm = serializers.BooleanField(read_only=True)
    employee = EmployeeSerialize_Min(many=True, read_only=True)
    notes = serializers.SerializerMethodField()
    class Meta:
        model = Milestones
        fields = ['pk', 'name', 'deadline_date', 'quotity', 'status', 'desc', 'type', 'get_type_display', 'project', 
                  'employee',
                  'has_perm', 
                  'notes',
                  ]  
    def get_notes(self,obj):
       return GenericNote.objects.filter(
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk
        ).count()

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
    origin=serializers.SerializerMethodField()
    class Meta:
        model = Leave
        fields = ['pk', 'employee', 'employee_pk', 'type', 'type_pk', 
                  'start', 'start_period_di', 'end', 'end_period_di', 'title', 'color', 'comment','resourceId',
                  'origin',
                  ]  
    def get_origin(self,obj):
        return 'lm'
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
        if obj.content_type.model == 'institution':
            return reverse('orga_single', kwargs={
                'pk':obj.object_id,
                'app':'project',
                'model':'institution'
                })
        if obj.content_type.model == 'fund_institution':
            return reverse('orga_single', kwargs={
                'pk':obj.object_id,
                'app':'fund',
                'model':'fund_institution'
                })

        return "-"
    
# --------------------------------------------------------------------------------------- #
# ---------------------------    APP PROJECT / SERIALISZER    --------------------------- #
# --------------------------------------------------------------------------------------- #


  
class Institution_ProjectParticipantSerializer(serializers.ModelSerializer):
    institution=InstitutionSerializer(many=False, read_only=True)
    status_name=serializers.CharField(source='get_status_display')
    has_perm = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Institution_Participant
        fields = ['pk', 'institution','status', 'status_name', 
                  'has_perm',
                  ] 
               
class Institution_ParticipantSerializer(serializers.ModelSerializer):
    project=ProjectSerializer(many=False, read_only=True)
    institution=InstitutionSerializer(many=False, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Institution_Participant
        fields = ['pk', 'project', 'institution', 'status', 
                  'has_perm',
                  ]  

class ParticipantSerializer(serializers.ModelSerializer):
    status=serializers.SerializerMethodField()
    project=ProjectSerializer(many=False, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Participant
        # fields = ['pk', 'project_pk', 'project_name', 'project_start_date', 'project_end_date', 'project_status', 'status', 'quotity' ]
        fields = ['pk', 'project', 'start_date', 'end_date', 'status', 'quotity', 'is_active',
                  'has_perm',
                  ]
    
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
    
    
class FundItemSerializeContract(serializers.ModelSerializer):
    fund=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    contract_effective=serializers.SerializerMethodField()
    amount_left_effective=serializers.SerializerMethodField()
    contract_prov=serializers.SerializerMethodField()
    amount_left_prov=serializers.SerializerMethodField()

    class Meta:
        model = Fund_Item
        fields = ['pk', 'type', 'fund','amount',  'expense','available','value_date', 'entry_date',
                  'contract_effective','amount_left_effective',
                  'contract_prov','amount_left_prov',
                  ] 
            
    def get_contract_effective(self,obj):
        from expense.models import Contract
        ct = Contract.objects.filter(fund = obj.fund, is_active = True, status="effe")
        return ct.count()
    def get_amount_left_effective(self,obj): 
        ct = Contract.objects.filter(fund = obj.fund, is_active = True, status="effe")
        amount = 0 
        for c in ct :
            amount += c.remain_amount
        return amount
    
    def get_contract_prov(self,obj):
        from expense.models import Contract
        ct = Contract.futur.filter(fund = obj.fund, status="prov")
        return ct.count()
    
    def get_amount_left_prov(self,obj): 
        ct = Contract.objects.filter(fund = obj.fund, status="prov")
        amount = 0 
        for c in ct :
            amount += c.remain_amount
        return amount
    
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
    has_perm = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Fund
        fields = ['pk', 'funder', 'institution', 'start_date', 'end_date', 'ref', 
                  'amount', 'is_active', 'expense', 'available',
                   'amount_f', 'expense_f', 'available_f',
                   'has_perm',
                   ] 
        
    # def get_amount(self,obj):
    #     return Fund_Item.objects.filter(fund=obj.pk).aggregate(Sum('amount'))["amount__sum"]

class ExpensePOintSerializer(serializers.ModelSerializer):
    fund=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    class Meta:
        model = Expense_point
        fields = ['pk', 'entry_date', 'value_date', 'fund', 'type', 'amount']
        
class ExpenseSerializer(serializers.ModelSerializer):
    fund_item=FundSerialize(many=False, read_only=True)
    type=CostTypeSerialize(many=False, read_only=True)
    status = serializers.SerializerMethodField()
    contract = serializers.SerializerMethodField() 
    class_type = serializers.SerializerMethodField() 
    class Meta:
        model = Expense
        fields = ['pk', 'expense_id', 'date', 'fund_item', 'type', 'status',  'amount',
                  'desc',
                  'contract',
                  'class_type',
                  ]   
    
    def get_status(self,obj):
        return obj.get_status_display() 
    
    def get_contract(self, obj):
        # Vérifie si l'objet est une instance de Contract_expense
        if isinstance(obj, Contract_expense):
            return ContractSerializerSimple(obj.contract, many=False).data  # ou retourner plus de détails si nécessaire
        return None    
    def get_class_type(self,obj):
        return type(obj).__name__
# ---------------------------------------------------------------------------------------- #
# ---------------------------    APP Expense / SERIALISZER    --------------------------- #
# ---------------------------------------------------------------------------------------- #
class ContractSerializerSimple(serializers.ModelSerializer):
    contract_type = serializers.SerializerMethodField()
    class Meta:
        model = Contract
        fields = ['pk', 'employee', 'start_date', 'end_date', 'fund', 'contract_type', 'quotity', 'is_active','status',
                  ]
    def get_contract_type(self,obj):
        if obj.contract_type:
            return obj.contract_type.name
        return None 
    
class ContractSerializer(serializers.ModelSerializer):
    fund = FundSerialize(many=False, read_only=True)
    contract_type = serializers.SerializerMethodField()
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Contract
        fields = ['pk', 'employee', 'start_date', 'end_date', 'fund', 'contract_type','total_amount', 'quotity', 'is_active','status',
                  'has_perm',
                  ]
    
    def get_contract_type(self,obj):
        if obj.contract_type:
            return obj.contract_type.name
        return None 

class ContractSerializerSimple(serializers.ModelSerializer):
    contract_type = serializers.SerializerMethodField()
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    class Meta:
        model = Contract
        fields = ['pk', 'employee', 'start_date', 'end_date','contract_type','total_amount', 'quotity', 'is_active','status']
    
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
        fields = ['pk', 'expense_id', 'date', 'type', 'status', 'fund', 'amount']
        
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
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Employee_Superior
        fields = ['pk', 'employee','employee_superior', 'start_date', 'end_date', 
                  'is_active',
                  'has_perm',
                  ]
class EmployeeSubordinateSerialize(serializers.ModelSerializer):
    subordinate=EmployeeSerialize_Min(many=False, read_only=True, source='employee')
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Employee_Superior
        fields = ['pk', 'subordinate','employee', 'start_date', 'end_date', 
                  'is_active',
                  'has_perm',
                  ]       
        
from django.http import JsonResponse       
class EmployeeOrganizationChartSerialize(serializers.ModelSerializer):
    status = EmployeeStatusSerialize(many=True, read_only=True, source='get_status')
    subordinate = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
   
    class Meta:
        model = Employee
        fields = ['pk', 'user_name', 'status',
                  'active', 
                  'subordinate', ]
    
    def get_active(self,obj):
        return True
    def get_subordinate(self,obj):
        show_pas = self.context.get("show_pas")
        if show_pas:
            sub = obj.get_current_subordinate()
        else:
            sub = obj.get_subordinate()
        # emp=Employee.objects.filter(pk__in=sub.values('employee'))
        return EmployeeOrganizationChartOrgSerialize(sub,many=True, context=self.context).data
    
class EmployeeOrganizationChartOrgSerialize(serializers.ModelSerializer):
    status = EmployeeStatusSerialize(many=True, read_only=True, source='employee.get_status')
    subordinate = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    pk = serializers.SerializerMethodField()
   
    class Meta:
        model = Employee
        fields = ['pk', 'user_name', 'status',
                  'active', 
                  'subordinate', ]
    def get_user_name(self,obj):
        return obj.employee.user_name
    def get_pk(self,obj):
        return obj.employee.pk
    def get_active(self,obj):
        return obj.is_active and obj.employee.is_active
    
    def get_subordinate(self,obj):
        show_pas = self.context.get("show_pas")
        if show_pas:
            sub = obj.employee.get_current_subordinate()
        else:
            sub = obj.employee.get_subordinate()
        return EmployeeOrganizationChartOrgSerialize(sub,many=True, context=self.context).data

class IncommingEmployeeSerialize(serializers.ModelSerializer):
    superior=EmployeeSuperiorSerialize(many=True, read_only=True, source='get_superior')
    class Meta:
        model = Employee
        fields = ['pk','user_name', 'entry_date', 'exit_date',
                  'superior',
                  ]
class EmployeeSerialize(serializers.ModelSerializer):
    user = UserSerializer(many=False, read_only=True)
    get_status =EmployeeStatusSerialize(many=True, read_only=True)
    # contracts=ContractSerializer(many=True, read_only=True)
    # projects=ParticipantSerializer(many=True, read_only=True)
    info=EmployeeInfoSerialize(many=True, read_only=True)
    superior=EmployeeSuperiorSerialize(many=True, read_only=True, source='get_current_superior')
    #has_subordinate=EmployeeSuperiorSerialize(many=True, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Employee
        fields = ['pk','first_name', 'last_name', 'user', 'birth_date', 'entry_date', 'exit_date','email',
                  'is_team_leader','is_team_mate','get_status','is_active',
                  'contracts_quotity',
                  'projects_quotity',
                  'info',
                  'superior','has_subordinate',
                  'has_perm',
                  ]
        
class TeamMateSerializer_min(serializers.ModelSerializer):
    employee=EmployeeSerialize_Min(many=False, read_only=True)
    class Meta:
        model = TeamMate
        fields=['pk', 'employee', 'start_date', 'end_date', 'is_active',]
    

class TeamSerializer_min(serializers.ModelSerializer):  
    url = serializers.SerializerMethodField()
    is_leader=serializers.BooleanField(read_only=True)
    class Meta:
        model= Team
        fields=['pk','name', 'url','is_leader',]
    
    def get_url(self, obj):
        return reverse('team_single', kwargs={'pk':obj.pk})
from operator import attrgetter    
class TeamSerializer(serializers.ModelSerializer):
    leader=EmployeeSerialize_Min(many=False, read_only=True)
    team_mate=serializers.SerializerMethodField()
    has_perm = serializers.BooleanField(read_only=True)
    
    class Meta:
        model= Team
        fields=['pk','name', 'leader', 'team_mate', 'has_perm']

    def get_team_mate(self, obj):
        tm = TeamMate.objects.filter(team=obj)
        sorted_team_mates = sorted(tm, key=lambda x: (not x.is_active, attrgetter('employee.first_name')(x)), reverse=False)
        return TeamMateSerializer_min(sorted_team_mates, many=True, read_only=True).data

class ParticipantProjectSerializer(serializers.ModelSerializer):
    employee=EmployeeSerialize_Min(many = False, read_only = True)
    status_name=serializers.SerializerMethodField()
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Participant
        fields = ['pk', 'employee', 'start_date', 'end_date', 'status', 'status_name', 'quotity', 
                  'has_perm',
                  ]
    
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
    participant = ParticipantProjectSerializer(many=True, read_only=True, source="get_participant")# serializers.SerializerMethodField() 
    # participant_count=serializers.SerializerMethodField()
    fund=FundProjectSerialize(many=True, read_only=True, source="get_funds") # serializers.SerializerMethodField() 
    institution=Institution_ProjectParticipantSerializer(many=True, read_only=True, source="get_institutions") # serializers.SerializerMethodField()
    # total_amount= serializers.SerializerMethodField()
    info=ProjectInfoSerialize(many=True, read_only=True)
    
    
    class Meta:
        model = Project
        fields = ['pk', 'name', 'start_date', 'end_date', 'status', 
                  'participant', 
                #   'participant_count',
                  'institution', 
                  'fund',
                #   'get_funds_amount', 'get_funds_expense','get_funds_available',
                #   'get_funds_amount_f', 'get_funds_expense_f','get_funds_available_f',
                  'info',
                  ]
    # def get_participant(self,obj):
    #     part = Participant.objects.select_related('employee').filter(project = obj.pk, employee__is_active= True)
    #     return ParticipantProjectSerializer(part , many=True).data
    
    # def get_participant_count(self,obj):
    #     part = Participant.objects.filter(project = obj.pk, employee__is_active= True).count()
    #     return part
    
    # def get_fund(self,obj):
    #     fund = Fund.objects.select_related('funder', 'institution').filter(project = obj.pk)
    #     return FundProjectSerialize(fund , many=True).data
    
    # def get_institution(self,obj):
    #     ip = Institution_Participant.objects.filter(project = obj.pk)
    #     return Institution_ProjectParticipantSerializer(ip , many=True).data
    
    # def get_total_amount(self,obj):
    #     fund = Fund.objects.filter(project = obj.pk)
    #     return Fund_Item.objects.filter(fund__in=fund).aggregate(Sum('amount'))["amount__sum"]
    
# ------------------------------------------------------------------------------------- #
# ---------------------------    APP infos / SERIALISZER    --------------------------- #
# ------------------------------------------------------------------------------------- #
from infos.models import ContactType, OrganizationInfos, Contact, InfoTypeClass, OrganizationInfosType, GenericNote
class OrgaInfoTypeSerializer(ProjectInfoTypeIconSerialize):
    icon_val=serializers.SerializerMethodField()
    class Meta:
        fields = ['pk', 'name', 'icon_val', 'type']
        model = OrganizationInfosType


class ContactTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactType
        fields = ['pk','name',]    
 
class ContactSerializer(serializers.ModelSerializer):
    type=ContactTypeSerializer(many=False, read_only=True)
    class Meta:
        model = Contact
        fields = ['pk','first_name','last_name','type', 'comment',]
        
          
class OrganizationInfoSerializer(serializers.ModelSerializer):
     content_type=ContentTypeSerialize(many=False, read_only=True)
     info=OrgaInfoTypeSerializer(many=False, read_only=True)
     class Meta:
        model = OrganizationInfos
        fields = ['pk',
                  'content_type',
                  'object_id',
                  'info', 
                  'value', 'comment',]
            

class GenericInfoSerialiszer(serializers.ModelSerializer):
    content_type=ContentTypeSerialize(many=False, read_only=True)
    
    class Meta:
        model = GenericNote
        fields = ['pk',
                  'content_type',
                  'object_id',
                  'name', 
                  'note',
                  'created_at', 'updated_at', 
                  ]
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    APP Budget
class BudgetSerializer(serializers.ModelSerializer):
    # user = UserSerializer(many=False, read_only=True)
    cost_type=CostTypeSerialize(many=False, read_only=False)
    fund=FundSerialize(many=False, read_only=False)
    emp_type=EmployeeTypeSerialize(many=False, read_only=False)
    employee=EmployeeSerialize_Min(many=False, read_only=False)
    contract_type=ContractTypeSerializer(many=True, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Budget
        fields = ['pk', 'cost_type', 'fund', 'emp_type', 'employee', 'quotity', 'amount','contract_type', 'desc',
                  'has_perm',
                  ]  
    
class ContribSerializer(BudgetSerializer):
    # user = UserSerializer(many=False, read_only=True)
    cost_type=CostTypeSerialize(many=False, read_only=False)
    fund=FundSerialize(many=False, read_only=False)
    emp_type=EmployeeTypeSerialize(many=False, read_only=False)
    employee=EmployeeSerialize_Min(many=False, read_only=False)
    contract_type=ContractTypeSerializer(many=True, read_only=True)
    has_perm = serializers.BooleanField(read_only=True)
    class Meta:
        model = Contribution
        fields = ['pk', 'cost_type', 'fund', 'emp_type', 'employee', 'quotity', 'amount','contract_type','desc',
                  'start_date', 'end_date', 'is_active',
                  'has_perm'] 
        
        
        
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> For COntract Prospective
class EmployeeContractProsp(serializers.ModelSerializer):
    id = serializers.CharField(source='pk')
    status = EmployeeStatusSerialize(many=True, read_only=True, source='get_current_status')
    class Meta:
        model = Employee
        fields = ['id', 'user_name', 'status',] 
        
class ContractSerializer1DCal(serializers.ModelSerializer):
    resourceId= serializers.CharField(source='employee.pk')
    start=serializers.SerializerMethodField()
    end=serializers.SerializerMethodField()
    fund = FundSerialize(many=False, read_only=True)
    contract_type = serializers.SerializerMethodField()
    employee_username = serializers.CharField(source='employee.user_name')
    class Meta:
        model = Contract
        fields = ['pk', 'employee','employee_username',
                    'contract_type',  
                    'start',  'end',
                    'resourceId',
                    'fund', 
                    'total_amount','remain_amount',
                    'status',
                  ]  
    def get_start(self,obj):
        if obj.start_date:
            st= obj.start_date.isoformat()
            return st
        return None
    
    def get_end(self,obj):
        if obj.end_date:
            ed=datetime.combine(obj.end_date ,datetime.min.time())
            ed = ed +timedelta(days=1)
            return ed
        return None
    
    def get_contract_type(self,obj):
        if obj.contract_type:
            return obj.contract_type.name
        return None 
