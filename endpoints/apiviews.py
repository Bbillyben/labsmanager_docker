
from django.http import JsonResponse
from django.db.models import Q,Value, BooleanField
from django.utils import timezone
from datetime import datetime
from .models import Milestones
from .resources import MilestonesResource
from labsmanager import serializers 

from project.models import Project
from rest_framework import viewsets, permissions
from rest_framework.decorators import action

from labsmanager.helpers import DownloadFile

from dashboard import utils

class MilestonesViewSet(viewsets.ModelViewSet):
    queryset = Milestones.objects.prefetch_related('project').all()
    serializer_class = serializers.MilestonesSerializer
    
    def list(self, request, *args, **kwargs):
        export = request.GET.get('export', None)
        if export is not None:
            qs = self.filter_queryset(self.get_queryset())
            return self.download_queryset(qs, export)
        return super().list( request, *args, **kwargs)
    
    def download_queryset(self, queryset, export_format):
        """Download the filtered queryset as a data file"""
        dataset = MilestonesResource().export(queryset=queryset)
        filedata = dataset.export(export_format)
        dateSuffix=datetime.now().strftime("%Y%m%d-%H%M")
        filename = f"Milestones_{dateSuffix}.{export_format}"
        return DownloadFile(filedata, filename) 
    
    def filter_queryset(self, request, queryset):
        params = self.request.query_params
        
        status = params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        curr_date = timezone.now().date()
        
        delayed = params.get('delayed', None)
        if delayed and delayed=="1":
            queryset = queryset.filter(status=False, end_date__lte=curr_date)
        
        incomming = params.get('incomming', None)
        if incomming and incomming=="1":
            queryset = queryset.filter(status=False, end_date__gte=curr_date)
            
        type_endpoint = params.get('type_endpoint', None)
        if type_endpoint:
            if type_endpoint=="task":
                queryset = queryset.filter(start_date__isnull=False)
            else:
                queryset = queryset.filter(start_date__isnull=True)
        return queryset
    
    @action(methods=['get'], detail=False, url_path='project/(?P<pj_pk>[^/.]+)', url_name='project')
    def project(self, request, pj_pk=None, pk=None):
        t1=self.filter_queryset(request, self.queryset.filter(project=pj_pk))
        export = request.GET.get('export', None)
        if export:
            return self.download_queryset(t1, export)
        try:
            proj = Project.objects.get(pk=pj_pk)
            if request.user.has_perm("project.change_project", proj):
                t1 = t1.annotate(has_perm=Value(True))
        except:
            pass                                  
        return JsonResponse(serializers.MilestonesSerializer(t1, many=True,  context={'request': request}).data, safe=False)

    @action(methods=['get'], detail=False, url_path='employee/(?P<emp_pk>[^/.]+)', url_name='employee')
    def employee(self, request, emp_pk=None, pk=None):
        t1=self.filter_queryset(request, self.queryset.filter(employee=emp_pk))
        export = request.GET.get('export', None)
        if export:
            return self.download_queryset(t1, export)
        return JsonResponse(serializers.MilestonesSerializer(t1, many=True, context={'request': request}).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='milestones_stale', url_name='milestones_stale')
    def milestones_stale(self, request, pj_pk=None, pk=None):
        q_objects = Q(status=False) & Q(project__status=True) # base Q objkect
        slot = utils.getDashboardMilestonesTimeSlot(request)
        if 'from' in slot:
            q_objects = q_objects & Q(end_date__gte=slot["from"])
        if 'to' in slot:
            q_objects = q_objects & Q(end_date__lte=slot["to"])
            
        ms=self.queryset.filter(q_objects).order_by('end_date')
        
        return JsonResponse(serializers.MilestonesSerializer(ms, many=True, context={'request': request}).data, safe=False)
    
    
    