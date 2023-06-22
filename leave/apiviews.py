from django.http import JsonResponse
from django.db.models import Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast, Coalesce, Now, Extract, Abs
import datetime

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers 

from .models import Leave, Leave_Type
from staff.models import TeamMate, Employee_Status, Team
from project.models import Participant


from django.views.decorators.csrf import csrf_exempt
from collections.abc import Iterable

from .resources import LeaveItemResources
from labsmanager.helpers import DownloadFile

class LeaveViewSet(viewsets.ModelViewSet):
    queryset = Leave.objects.select_related('employee', 'type').all()
    serializer_class = serializers.LeaveSerializerBasic
    permission_classes = [permissions.IsAuthenticated]
    
    def filter_queryset(self, queryset):
        
        data={}
        if self.request.data:
            data.update(self.request.data)
        if self.request.query_params:
            for key in self.request.query_params:
                data[key]=self.request.query_params.get(key)
                
        if not data:
            return queryset
        
        qset=queryset
        types= data.get('type', None)
        if types is not None:
            if isinstance(types, str):
                types=types.split(',')
            elif not isinstance(types, Iterable):
                types=[types,]
                 
            if all([isinstance(item, int) for item in types]) or all([item.isdigit() for item in types]):
                qset= qset.filter(type__in=types)
            else:
                qset= qset.filter(type__short_name__in=types)
                     
        emp= data.get('employee', None)
       
        if emp is not None:
            if isinstance(emp, str):
                emp=emp.split(',')
            elif not isinstance(emp, Iterable):
                emp=[emp,]
            qset= qset.filter(employee__in=emp)
            
        emp_status= data.get('emp_status', None)
        if emp_status is not None and emp_status.isdigit() :
            empS=Employee_Status.current.filter(type=emp_status).values('employee')
            qset= qset.filter(employee__in=empS)
        
        team = data.get('team', None)
        print(team)
        print(team.isdigit())
        if team is not None and team.isdigit():
            tm = TeamMate.objects.filter(team=team).values('employee')
            tl=Team.objects.filter(pk=team).values("leader")
            qset= qset.filter(Q(employee__in=tm) | Q(employee__in=tl))
            
            
        project = data.get('project', None)
        if project is not None:
            pa = Participant.objects.filter(project=project).values('employee')
            qset= qset.filter(Q(employee__in=pa))
        
        start_date= data.get('start', None) 
        if start_date is not None:
            if isinstance(start_date, list):
                start_date=start_date[0] 
            start_date=start_date.split("T")[0]
            query=Q(start_date__gte=start_date) | (Q(start_date__lt=start_date) & Q(end_date__gte=start_date))
            qset= qset.filter(query)
        
        end_date= data.get('end', None) 
        if end_date is not None:
            if isinstance(end_date, list):
                end_date=end_date[0]
            end_date=end_date.split("T")[0]
            query=Q(end_date__lte=end_date) | (Q(start_date__lt=end_date) & Q(end_date__gte=end_date))
            qset= qset.filter(query)
        
        return qset
        
    
    def data(self, request, format=None):
        return Response("ok")
    
    def list(self, request, *args, **kwargs):
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = LeaveItemResources().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"LeaveItem_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename)
    
    @action(methods=['get'], detail=False, url_path='employee/(?P<emp_pk>[^/.]+)', url_name='employee')
    def search_employee(self, request, emp_pk=None):
        request.data.update({"employee":int(emp_pk),})
        qset=self.filter_queryset(self.queryset) 
        
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(qset)
            return self.download_queryset(qs, export)
        
        return Response(serializers.LeaveSerializer1D(qset, many=True).data)
    
    
    @action(methods=['get'], detail=False, url_path='calendar', url_name='search-calendar')
    def search_calendar(self, request):
        qset=self.filter_queryset(self.queryset) 
        
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(qset)
            return self.download_queryset(qs, export)   
        
        
        is_cal=request.data.get('cal',  request.query_params.get('cal', None))
        
        if request.data.get('cal', None) or request.query_params.get('cal', None):
            return Response(serializers.LeaveSerializer1DCal(qset, many=True).data)
        else:
            return Response(serializers.LeaveSerializer1D(qset, many=True).data)
    
    @action(methods=['post'], detail=False, url_path='search', url_name='search')
    def search(self, request):
        qset=self.filter_queryset(self.queryset)   
        return Response(serializers.LeaveSerializer1D(qset, many=True).data)
        
    
    
### VACATION AND DAY OFF EVENT retrieval
from labsmanager import settings
from django.http import JsonResponse
import json
from settings.models import LabsManagerSetting

def get_vacation_events(request):
    folder = str(settings.MEDIA_ROOT) + "/vacation"
    path = folder+"/vac.json"
    with open(path) as json_file:
        file_contents = json_file.read()
    vac_json = json.loads(file_contents)
    path = folder+"/dayoff.json"
    with open(path) as json_file:
        file_contents = json_file.read()
    dayoff_json = json.loads(file_contents)
    
    
    
    zone = LabsManagerSetting.get_setting("VACATION_ZONE")

    if "start" in request.GET:
        start= request.GET["start"]
        start= datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
    else:
        start = datetime.datetime(datetime.MINYEAR, 1, 1)
    if "end" in request.GET:
        end = request.GET["end"]
        end= datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M:%SZ")
    else:
        end = datetime.datetime(datetime.MAXYEAR, 12, 31)
        
    bg_color_vac="lightblue"
    bg_color_off="lightskyblue"
    
    
    start = start.replace(tzinfo=None)
    end = end.replace(tzinfo=None)
    
    data=[]
    unik=[]
    for v in vac_json:
        if v['zones'] != zone:
            continue
        if v['start_date'] in unik:
            continue
        unik.append(v['start_date'])
        
        s=datetime.datetime.strptime(v['start_date'], "%Y-%m-%dT%H:%M:%S%z")
        e=datetime.datetime.strptime(v['end_date'], "%Y-%m-%dT%H:%M:%S%z")
        s = s.replace(tzinfo=None)
        e = e.replace(tzinfo=None)
        if (start<=e and s<=end):
            tmp={
                'start': s.strftime('%Y-%m-%d'),
                'end': e.strftime('%Y-%m-%d'),
                'zone': v['zones'],
                'desc': v['description'],
                'display': 'background',
                'color': bg_color_vac,
            }
            data.append(tmp)
            
    for item in dayoff_json:
        d=datetime.datetime.strptime(item, "%Y-%m-%d")
        d = d.replace(tzinfo=None)
        if (start<=d and d<=end):
            tmp={
                'start': item,
                #'end': e.strftime('%Y-%m-%d'),
                'desc': dayoff_json[item],
                'display': 'background',
                'color': bg_color_off,
            }
            data.append(tmp)
        
    return  JsonResponse(data, safe=False)


def get_vacation_zones_choices():
    folder = str(settings.MEDIA_ROOT) + "/vacation"
    path = folder+"/vac.json"
    with open(path) as json_file:
        file_contents = json_file.read()
    vac_json = json.loads(file_contents)
    listZone = []
    unik = []
    for item in vac_json:
        if not item["zones"] in unik:
            listZone.append((item["zones"], item["zones"]))
            unik.append(item["zones"])
    listZone.sort(key=lambda x: x[1])
    return listZone

def get_vacation_location_choices():
    folder = str(settings.MEDIA_ROOT) + "/vacation"
    path = folder+"/vac.json"
    with open(path) as json_file:
        file_contents = json_file.read()
    vac_json = json.loads(file_contents)
    listZone = []
    unik = []
    for item in vac_json:
        if not item["location"] in unik:
            listZone.append((item["location"], item["location"]))
            unik.append(item["location"])
    listZone.sort(key=lambda x: x[1])
    return listZone
    