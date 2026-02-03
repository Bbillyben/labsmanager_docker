from django.http import JsonResponse
from django.db.models import Q, Value

from project.models import Participant, Project, Institution_Participant
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from labsmanager import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from expense.models import Contract
from fund.models import Fund
from labsmanager.utils import str2bool
from .filters import ProjectFilter
from .resources import ProjectResource
from labsmanager.helpers import DownloadFile
from labsmanager.utils import clean_iso_date
from endpoints.models import Milestones
from staff.models import Team, TeamMate

from datetime import datetime

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.prefetch_related('participant_project').all()
    serializer_class = serializers.ProjectFullSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ProjectFilter
    
    def get_queryset(self, *arg, **kwargs):

        qset = super().get_queryset( *arg, **kwargs)
        qset = Project.get_instances_for_user('view', self.request.user, qset)
        qset = qset.annotate(has_perm=Value(True))
        
        return qset
    
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
        if funder is not None and funder.isdigit():
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
        if institution_name is not None and institution_name.isdigit() :
            pjI=Institution_Participant.objects.filter(institution=institution_name).values('project')
            pjF=Fund.objects.filter(institution=institution_name).values('project')
            queryset = queryset.filter(pk__in=pjI.union(pjF))
        
        team =params.get('team', None)
        if team is not None and team.isdigit():
            tm = TeamMate.objects.filter(team=team).values('employee')
            tl=Team.objects.filter(pk=team).values("leader")
            proj_part= Participant.objects.filter(Q(employee__in=tm) | Q(employee__in=tl)).values('project')
            queryset = queryset.filter(pk__in = proj_part)
            
        
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
        t1 = Participant.annotate_queryset(t1, request.user, "view")
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
        
        if request.user.has_perm("project.change_project", proj):
                t1 = t1.annotate(has_perm=Value(True))
                
        return JsonResponse(serializers.FundProjectSerialize(t1, many=True).data, safe=False)   
    
    @action(methods=['get'], detail=True,url_path='contracts', url_name='contracts')
    def contracts(self,request, pk=None):
        from expense.apiviews import ContractViewSet
        cv = ContractViewSet()
        request.query_params._mutable = True
        request.query_params.update({"project_id": int(pk)})
        cv.request = request
        
        export = request.GET.get('export', None)
        if export is not None:
            return cv.list(request)
        
        
        
        fund=Fund.objects.filter(project=pk).values('pk')  
        contractQS = cv.get_queryset()  
        contract=cv.filter_queryset(contractQS).filter(fund__in=fund).order_by('end_date')
        
        proj = self.get_object()
        if request.user.has_perm("project.change_project", proj):
                contract = contract.annotate(has_perm=Value(True))
                
                
        # contract=Contract.objects.filter(fund__in=fund).order_by('end_date')
        return JsonResponse(serializers.ContractSerializer(contract, many=True).data, safe=False)

    ######################
    # for project calendar
    ##################################################################
    ### For single project
    @action(methods=['get'], detail=True,url_path='calendar-get-event', url_name='calendar-get-event')
    def calendar_get_event(self,request, pk=None):
        slot={}
        if 'start' in request.GET :#request.GET['start']:
            slot['from']=clean_iso_date(request.GET['start'])
        if 'end' in request.GET:#['end']:
            slot['to']=clean_iso_date(request.GET['end'])
        
        proj = Project.objects.filter(pk = pk)
        proj_evt = serializers.ProjectProjectSerializer_cal(proj, many=True).data
        
        mils = Milestones.expired.timeframe(slot).filter(project = pk)
        evt_mil = serializers.ProjectMilestonesSerializer_cal(mils, many=True).data
        
        part = Participant.objects.filter(project = pk).order_by('status')
        evt_part = serializers.ProjectParticipantSerializer_cal(part, many=True).data
        
        fu = Fund.objects.filter(project = pk)
        evt_fu = serializers.ProjectFundSerializer_cal(fu, many=True).data
        
        evts = proj_evt + evt_mil + evt_part + evt_fu
        return Response(evts)  
    
    @action(methods=['get'], detail=True,url_path='calendar-get-resources', url_name='calendar-get-resources')
    def calendar_get_resources(self,request, pk=None):
        
        proj = Project.objects.filter(pk = pk)
        res_proj = serializers.ProjectResourceSerializer_cal_project(proj, many=True, context={'request': request}).data
        emp = Participant.objects.filter(project = pk).order_by('status')
        res_part = serializers.ProjectResourceSerializer_cal_participant(emp, many=True, context={'request': request}).data
        
        mils = Milestones.objects.filter(project = pk)
        res_mil = serializers.ProjectResourceSerializer_cal_milestones(mils, many=True, context={'request': request}).data
        
        
        fund = Fund.objects.filter(project = pk)
        res_fund = serializers.ProjectResourceSerializer_cal_fund(fund, many=True, context={'request': request}).data
        
        
        resources = res_proj + res_fund + res_mil + res_part
        
        return Response(resources)  
    
    ### For general project calendar
    def filter_project_for_calendar(self, request, queryset):
        query = Q()
        team =request.GET.get('team', None)
        if team is not None and team.isdigit():
            tm = TeamMate.objects.filter(team=team).values('employee')
            tl=Team.objects.filter(pk=team).values("leader")
            proj_part= Participant.objects.filter(Q(employee__in=tm) | Q(employee__in=tl)).values('project')
            query &= Q(pk__in = proj_part)

        return queryset.filter(query)   
            
            
    @action(methods=['get'], detail=False, url_path='calendar-all-get-event', url_name='calendar-all-get-event')
    def calendar_all_get_event(self,request):
        # print("########################## ALL PROJECT CALENDAR CALL ##########################")
        # print(request.GET)
        
        slot={}
        if 'start' in request.GET :#request.GET['start']:
            slot['from']=clean_iso_date(request.GET['start'])
        if 'end' in request.GET:#['end']:
            slot['to']=clean_iso_date(request.GET['end'])
        
        projects_slots  = Project.time_object.timeframe(slot)
        proj = Project.get_instances_for_user('view', self.request.user, projects_slots)
        self.request = request
        proj = self.filter_queryset(proj)
       
            
            
        raw_items= request.GET.get('proj_items', '')
        items = raw_items.split(',') if raw_items else []
        
        
        evts = []
        if 'project' in items:
            res_proj =  serializers.ProjectProjectSerializer_cal(proj, many=True).data
            evts.extend(res_proj)

        if 'participant' in items:
            part = Participant.objects.filter(project__in = proj).order_by('status')
            evt_part = serializers.ProjectParticipantSerializer_cal(part, many=True).data
            evts.extend(evt_part)

        if 'milestone' in items:
            mils = Milestones.expired.timeframe(slot).filter(project__in = proj).order_by("end_date")
            evt_mil = serializers.ProjectMilestonesSerializer_cal(mils, many=True).data
            evts.extend(evt_mil)

        if 'fund' in items:
            fu = Fund.objects.filter(project__in = proj)
            evt_fu = serializers.ProjectFundSerializer_cal(fu, many=True).data
            evts.extend(evt_fu)
        return Response(evts) 
    
    @action(methods=['get'], detail=False,url_path='calendar-all-get-resources', url_name='calendar-all-get-resources')
    def calendar_all_get_resources(self,request):
        # print("########################## ALL PROJECT CALENDAR RESSOURCES ##########################")
        # print(request.GET)
        slot={}
        if 'start' in request.GET :#request.GET['start']:
            slot['from']=clean_iso_date(request.GET['start'])
        if 'end' in request.GET:#['end']:
            slot['to']=clean_iso_date(request.GET['end'])
            
        
        projects_slots  = Project.time_object.timeframe(slot)
        projects = Project.get_instances_for_user('view', self.request.user, projects_slots)
        self.request = request
        projects = self.filter_queryset(projects)
            
            
        raw_items= request.GET.get('proj_items', '')
        items = raw_items.split(',') if raw_items else []
        
        resources = []
        if 'project' in items:
            res_proj = serializers.ProjectResourceSerializer_gencal_project(projects, many=True, context={'request': request}).data
            for i, item in enumerate(res_proj):
                item['group_order'] = f"a_{i}"
            resources.extend(res_proj)

        if 'participant' in items:
            participants = Participant.objects.filter(project__in=projects).order_by('status')
            res_part = serializers.ProjectResourceSerializer_gencal_participant(participants, many=True, context={'request': request}).data
            for i, item in enumerate(res_part):
                item['group_order'] = f"c_{i}"
            resources.extend(res_part)

        if 'milestone' in items:
            ms_status = request.GET.get('milestone', '')
            match ms_status:
                case 'ongoing':
                    milestones = Milestones.objects.filter(project__in=projects, status = False).order_by("end_date")
                case 'comp':
                    milestones = Milestones.objects.filter(project__in=projects, status = True).order_by("end_date")
                case 'delayed':
                    milestones = Milestones.expired.overdue().filter(project__in=projects).order_by("end_date")
                case _: # group also empty an 'all'
                    milestones = Milestones.objects.filter(project__in=projects).order_by("end_date")

            res_mil = serializers.ProjectResourceSerializer_gencal_milestones(milestones, many=True, context={'request': request}).data
            for i, item in enumerate(res_mil):
                item['group_order'] = f"e_{i}"
            resources.extend(res_mil)

        if 'fund' in items:
            funds = Fund.objects.filter(project__in=projects)
            res_fund = serializers.ProjectResourceSerializer_cal_fund(funds, many=True, context={'request': request}).data
            for i, item in enumerate(res_fund):
                item['group_order'] = f"b_{i}"
            resources.extend(res_fund)

        return Response(resources) 