from django.http import JsonResponse
from django.db.models import Q

from project.models import Participant
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from staff.models import Employee, Employee_Status, Team, TeamMate
from expense.models import  Contract
from project.models import Participant, Project

from labsmanager.utils import str2bool
from labsmanager.helpers import DownloadFile


from staff.filters import EmployeeFilter

from .ressources import EmployeeResource, TeamResource

from datetime import datetime

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
             
        empStatus = params.get('status', None)
        if empStatus:
            inS=Employee_Status.objects.filter(type=empStatus).values('employee')
            queryset = queryset.filter(pk__in=inS)
        
        return queryset
    
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
    
    @action(methods=['get'], detail=True,url_path='contracts', url_name='contracts')
    def contracts(self,request, pk=None):
        emp = self.get_object()
        contract=Contract.objects.filter(employee=emp.pk).order_by('end_date')
        return JsonResponse(serializers.ContractSerializer(contract, many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=True, url_path='teams', url_name='teams')
    def teams(self, request, pk=None):
        emp = self.get_object()
        t1=Team.objects.filter(leader=emp.pk)
        tm = TeamMate.objects.filter(employee=emp.pk).values('team')
        t2=Team.objects.filter(pk__in=tm)
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
        if team is not None:
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
    
class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related('leader').all()
    serializer_class = serializers.TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    
    
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
        parti=Participant.objects.filter(Q(employee__in=mate) | Q(employee=team.leader)).distinct('project') #.values("project")
        #pjset=Project.objects.filter(pk__in=parti)
        
        return JsonResponse(serializers.TeamParticipantSerializer(parti, many=True).data, safe=False)
        #return JsonResponse(serializers.TeamProjectSerializer(pjset, many=True).data, safe=False) 
        
        