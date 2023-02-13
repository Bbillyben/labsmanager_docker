from django.http import JsonResponse
from django.db.models import Q

from project.models import Participant, Project, Institution_Participant
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from expense.models import Contract
from fund.models import Fund
from labsmanager.utils import str2bool
from .filters import ProjectFilter
from .resources import ProjectResource
from labsmanager.helpers import DownloadFile

from datetime import datetime

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('participant_project').all()
    serializer_class = serializers.ProjectFullSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ProjectFilter
    
    
    def filter_queryset(self, queryset):
        params = self.request.query_params
        queryset = super().filter_queryset(queryset)
        
        status = params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        pname = params.get('project_name', None)
        if pname:
            queryset = queryset.filter(name__icontains=pname)
            
        isStale = params.get('stale', None)
        
        if isStale is not None :
            if str2bool(isStale):
                queryset = queryset.filter(Project.staleFilter())
            else:
                queryset = queryset.exclude(Project.staleFilter())
        
        funder = params.get('funder', None)   
        if funder is not None :
            pjF=Fund.objects.filter(funder=funder).values('project')
            queryset = queryset.filter(pk__in=pjF)
            
        fundref = params.get('fundref', None)   
        if fundref is not None :
            pjFr=Fund.objects.filter(ref__icontains=fundref).values('project')
            queryset = queryset.filter(pk__in=pjFr)
            
        participant_name= params.get('participant_name', None)   
        if participant_name is not None :
            pjP=Participant.objects.filter(Q(employee__first_name__icontains=participant_name) | Q(employee__last_name__icontains=participant_name)).values('project')
            queryset = queryset.filter(pk__in=pjP)
        
        institution_name= params.get('institution_name', None)  
        if institution_name is not None :
            pjI=Institution_Participant.objects.filter(institution=institution_name).values('project')
            queryset = queryset.filter(pk__in=pjI)
        
        return queryset
    
    
    def list(self, request, *args, **kwargs):
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = ProjectResource().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"Projects_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename)
        # return JsonResponse('not a test', safe=False)
            
    @action(methods=['get'], detail=True, url_path='participant', url_name='participant')
    def participant(self, request, pk=None):
        proj = self.get_object()
        t1=Participant.objects.filter(project=proj.pk)
        return JsonResponse(serializers.ParticipantProjectSerializer(t1, many=True).data, safe=False)

    @action(methods=['get'], detail=True, url_path='institution', url_name='institution')
    def institution(self, request, pk=None):
        proj = self.get_object()
        t1=Institution_Participant.objects.filter(project=proj.pk)
        return JsonResponse(serializers.Institution_ProjectParticipantSerializer(t1, many=True).data, safe=False)

    @action(methods=['get'], detail=True, url_path='funds', url_name='funds')
    def funds(self, request, pk=None):
        proj = self.get_object()
        t1=Fund.objects.filter(project=proj.pk)
        return JsonResponse(serializers.FundProjectSerialize(t1, many=True).data, safe=False)   
    
    @action(methods=['get'], detail=True,url_path='contracts', url_name='contracts')
    def contracts(self,request, pk=None):
        fund=Fund.objects.filter(project=pk).values('pk')        
        contract=Contract.objects.filter(fund__in=fund).order_by('end_date')
        return JsonResponse(serializers.ContractSerializer(contract, many=True).data, safe=False)
