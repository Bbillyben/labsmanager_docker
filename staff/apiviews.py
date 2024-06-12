from django.http import JsonResponse
from django.db.models import Q

from project.models import Participant
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from staff.models import Employee, Employee_Status, Team, TeamMate, Employee_Superior
from expense.models import  Contract
from project.models import Participant, Project

from labsmanager.utils import str2bool
from labsmanager.helpers import DownloadFile


from staff.filters import EmployeeFilter

from .ressources import EmployeeResource, TeamResource

from datetime import datetime
from django.db.models import BooleanField, Case, When, Value

from settings.models import LMUserSetting

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Employee to be viewed or edited.
    """
    queryset = Employee.objects.select_related('user').all()
    serializer_class = serializers.EmployeeSerialize
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = EmployeeFilter
    
    def filter_queryset(self, queryset):
        params = self.request.query_params
        queryset = super().filter_queryset(queryset)

        is_active = params.get('active', None)
        if is_active:
            queryset = queryset.filter(is_active=is_active)
        
        name = params.get('name', None)
        if name:
            queryset = queryset.filter( Q(first_name__icontains=name) | Q(last_name__icontains=name))
            
        sup_name = params.get('superior_name', None)
        if sup_name:
            empsup=Employee_Superior.current.filter(Q(superior__first_name__icontains=sup_name) | Q(superior__last_name__icontains=sup_name)).values('employee')
            queryset = queryset.filter(pk__in=empsup)
            
        empStatus = params.get('status', None)
        if empStatus:
            inS=Employee_Status.objects.filter(type=empStatus).values('employee')
            queryset = queryset.filter(pk__in=inS)
            
        current_status = params.get('current_status', None) 
        if current_status:
            inS=Employee_Status.current.filter(type=current_status).values('employee')
            queryset = queryset.filter(pk__in=inS)
        
        return queryset
    
    def get_queryset(self, *arg, **kwargs):

        qset = super().get_queryset( *arg, **kwargs)
        if self.request.user.has_perm('staff.view_employee'):
            qset = qset.annotate(has_perm=Value(True))
        else:    
            qset = qset.annotate(
                has_perm=Case(
                    When(Q(user=self.request.user), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )
        return qset
    
    def list(self, request, *args, **kwargs):
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = EmployeeResource().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"Employee_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename)
        # return JsonResponse('not a test', safe=False)
    
    @action(methods=['get'], detail=True,url_path='status', url_name='status')
    def status(self, request, pk=None):
        status = Employee_Status.objects.filter(employee=pk).order_by('end_date')
        return JsonResponse(serializers.EmployeeStatusSerialize(status,many=True).data, safe=False)
    
    @action(methods=['get'], detail=True,url_path='superior', url_name='superior')
    def superior(self, request, pk=None):
        superior = Employee_Superior.objects.filter(employee=pk).order_by('end_date')
        return JsonResponse(serializers.EmployeeSuperiorSerialize(superior,many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=True,url_path='contracts', url_name='contracts')
    def contracts(self,request, pk=None):
        from expense.apiviews import ContractViewSet
        emp = self.get_object()
        cvs = ContractViewSet() 
        cvs.request = request
        contract=cvs.filter_queryset(cvs.get_queryset())
        contract= contract.filter(employee=emp.pk).order_by('end_date')
        # Contract.objects.filter(employee=emp.pk).order_by('end_date')
        return JsonResponse(serializers.ContractSerializer(contract, many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=True, url_path='teams', url_name='teams')
    def teams(self, request, pk=None):
        emp = self.get_object()
        t1=Team.objects.filter(leader=emp.pk)
        t1 = t1.annotate(has_perm=Value(True))
        tm = TeamMate.objects.filter(employee=emp.pk).values('team')
        t2=Team.objects.filter(pk__in=tm)
        if self.request.user.has_perm('staff.view_team'):
            t2 = t2.annotate(has_perm=Value(True))
        else:    
            t2 = t2.annotate(has_perm=Value(False))
        
        t=t1.union(t2)
        
        
        
        return JsonResponse(serializers.TeamSerializer(t, many=True).data, safe=False)
    
    @action(methods=['get'], detail=True, url_path='projects', url_name='projects')
    def projects(self, request, pk=None):
        emp = self.get_object()
        t1=Participant.objects.filter(employee=emp.pk)
        
        return JsonResponse(serializers.ParticipantSerializer(t1, many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='calendar-resource', url_name='calendar-resource')
    def employee_calendar(self, request, pk=None):
        emp = request.data.get('employee', request.query_params.get('employee', None))
        if emp is not None:
            if isinstance(emp, str):
                emp=emp.split(',')
            elif not isinstance(emp, Iterable):
                emp=[emp,]
            t1=Employee.objects.filter(pk__in=emp).order_by('first_name')
        else:
            t1=Employee.objects.filter(is_active=True).order_by('first_name')
            
            
        team = request.data.get('team', request.query_params.get('team', None))
        if team is not None and team.isdigit():
            tm = TeamMate.objects.filter(team=team).values('employee')
            tl=Team.objects.filter(pk=team).values("leader")
            t1= t1.filter(Q(pk__in=tm)|Q(pk__in=tl))
        
        project = request.data.get('project', request.query_params.get('project', None))
        if project is not None:
            pj = Participant.objects.filter(project=project).values('employee')
            t1= t1.filter(Q(pk__in=pj))
        
        emp_status = request.data.get('emp_status', request.query_params.get('emp_status', None))
        if emp_status is not None and emp_status.isdigit() :
            empS=Employee_Status.current.filter(type=emp_status).values('employee')
            t1= t1.filter(pk__in=empS)
        
        return JsonResponse(serializers.EmployeeSerialize_Cal(t1, many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='contract-resource', url_name='contract-resource')
    def employee_contract(self, request, pk=None):
        sts = Employee_Status.current.filter(Q(is_contractual="c")).values('employee')
        t1=Employee.objects.filter(pk__in=sts, is_active= True).order_by('first_name')
        return JsonResponse(serializers.EmployeeContractProsp(t1, many=True).data, safe=False)
        
    @action(methods=['get'], detail=False, url_path='organization-chart', url_name='organization-chart')
    def organization_chart(self, request, pk=None):
        # get user preference to see past organization
        show_pas = LMUserSetting.get_setting("SHOW_PAST_ORG", user=request.user)
        
        no_sup=Employee_Superior.objects.all().values("employee")
        emp = Employee.objects.filter(Q(is_active=True) & ~Q(pk__in=no_sup))
        return JsonResponse(serializers.EmployeeOrganizationChartSerialize(emp, many=True, context={'show_pas': show_pas}).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='incomming-employee', url_name='incomming-employee')
    def incomming_employee(self, request):
        emp = Employee.get_incomming(relativedelta(months=+2)) #.objects.filter(query).order_by('entry_date')
        return JsonResponse(serializers.IncommingEmployeeSerialize(emp, many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=True, url_path='emp_team_lead', url_name='emp_team_lead')
    def emp_team_lead(self, request, pk=None):
        tm = TeamMate.objects.filter(employee=pk).values('team')
        tl=Team.objects.filter(Q(pk__in=tm)|Q(leader=pk)).annotate(
            is_leader=Case(
                When(leader__pk=pk, then=Value(True)), 
                default=Value(False),
                output_field=BooleanField())
            )

        return JsonResponse(serializers.TeamSerializer_min(tl, many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=True, url_path='emp_organization', url_name='emp_organization')
    def emp_organization(self, request, pk=None):
        
        # get user preference to see past organization
        show_pas = LMUserSetting.get_setting("SHOW_PAST_ORG", user=request.user)
        
        emp = Employee.objects.get(pk=pk)
        if show_pas:
            c_down = Employee_Superior.current.filter(superior = emp, employee__is_active=True)
        else:
            c_down = Employee_Superior.objects.filter(superior = emp)
            
        # build child
        c_node = {'sup':serializers.EmployeeSerialize_Min(emp, many=False).data, 'current':True, 'sub':[]}
        if c_down.exists():
            for down in c_down:
                c_node['sub'].append({'sup':serializers.EmployeeSerialize_Min(down.employee, many=False).data, 'is_active':down.is_active, 'sub':[]})
                self.__class__.build_tree_down(down.employee, c_node['sub'][len(c_node['sub']) - 1])
        
        c_sup = Employee_Superior.objects.filter(employee = emp)
        tree={}
        Full_Tree=[]
        if c_sup.exists():
            for sup in c_sup:
                tree['sup']=serializers.EmployeeSerialize_Min(sup.superior, many=False).data
                tree['sub']=[c_node.copy()]
                
                Full_Tree.append(self.__class__.build_tree_up(sup.superior, tree))
        else:
            Full_Tree.append(c_node)     
        return JsonResponse(Full_Tree, safe=False)
    
    
    
    @classmethod    
    def build_tree_down(cls, sup, tree):
        c_down = Employee_Superior.objects.filter(superior = sup)
        if c_down.exists():
            for sup2 in c_down:
                tree['sub'].append({'sup':serializers.EmployeeSerialize_Min(sup2.employee, many=False).data, 'sub':[]})
                cls.build_tree_down(sup2.employee, tree['sub'][len(tree['sub'])-1])
    
    @classmethod    
    def build_tree_up(cls, sup, tree):
        c_sup = Employee_Superior.objects.filter(employee = sup)
        child_tree = tree.copy()
        node={}
        if c_sup.exists() :
            for sup2 in c_sup:
                node['sup']=serializers.EmployeeSerialize_Min(sup2.superior, many=False).data
                node['sub']=[child_tree]
                node = cls.build_tree_up(sup2.superior, node)
                return node.copy()
        else:
            return child_tree
        
    
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('leader').all()
    serializer_class = serializers.TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    
    def get_queryset(self, *arg, **kwargs):

        qset = super().get_queryset( *arg, **kwargs)
       
        if self.request.user.has_perm('staff.view_team'):
            qset = qset.annotate(has_perm=Value(True))
        elif self.request.user.employee is not None:    
            qset = qset.annotate(
                has_perm=Case(
                    When(Q(leader=self.request.user.employee), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )
        return qset
    
    def filter_queryset(self, queryset):
        params = self.request.query_params
        queryset = super().filter_queryset(queryset)

        name = params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
        
        leader = params.get('leader', None)
        if leader is not None:
            queryset = queryset.filter(Q(leader__first_name__icontains=leader) | Q(leader__last_name__icontains=leader))
        
        mate = params.get('mate', None)
        if mate is not None:
            tm=TeamMate.objects.filter(Q(employee__first_name__icontains=mate) | Q(employee__last_name__icontains=mate)).values("team")
            queryset = queryset.filter(pk__in=tm)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = TeamResource().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"Team_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename)
    
    
    @action(methods=['get'], detail=True, url_path='projects', url_name='projects')
    def team_projects(self, request, pk=None):
        if pk is None:
            raise Exception("/api/team/<pk>/projects/ => No team Pk Found")
        team=self.queryset.filter(pk=pk).first()
        mate=TeamMate.objects.filter(team=team).values("employee")      
        parti=Participant.objects.filter((Q(employee__in=mate) | Q(employee=team.leader)) & Q(status__in=["l", "cl"])).distinct('project') #.values("project")
        #pjset=Project.objects.filter(pk__in=parti)
        
        return JsonResponse(serializers.TeamParticipantSerializer(parti, many=True).data, safe=False)
        #return JsonResponse(serializers.TeamProjectSerializer(pjset, many=True).data, safe=False) 
        
        