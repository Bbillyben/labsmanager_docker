
from django.http import JsonResponse
from django.db.models import Q,Value, BooleanField

from .models import Milestones
from labsmanager import serializers 

from project.models import Project
from rest_framework import viewsets, permissions
from rest_framework.decorators import action

from dashboard import utils

class MilestonesViewSet(viewsets.ModelViewSet):
    queryset = Milestones.objects.prefetch_related('project').all()
    serializer_class = serializers.MilestonesSerializer
    
    @action(methods=['get'], detail=False, url_path='project/(?P<pj_pk>[^/.]+)', url_name='project')
    def project(self, request, pj_pk=None, pk=None):
        t1=self.queryset.filter(project=pj_pk)
        try:
            proj = Project.objects.get(pk=pj_pk)
            if request.user.has_perm("project.change_project", proj):
                t1 = t1.annotate(has_perm=Value(True))
        except:
            pass                                  
        return JsonResponse(serializers.MilestonesSerializer(t1, many=True,  context={'request': request}).data, safe=False)

    @action(methods=['get'], detail=False, url_path='employee/(?P<emp_pk>[^/.]+)', url_name='employee')
    def employee(self, request, emp_pk=None, pk=None):
        t1=self.queryset.filter(employee=emp_pk)
        # try:
        #     proj = Project.objects.get(pk=pj_pk)
        #     if request.user.has_perm("staff.change_employee", proj):
        #         t1 = t1.annotate(has_perm=Value(True))
        # except:
        #     pass
        return JsonResponse(serializers.MilestonesSerializer(t1, many=True, context={'request': request}).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='milestones_stale', url_name='milestones_stale')
    def milestones_stale(self, request, pj_pk=None, pk=None):
        q_objects = Q(status=False) & Q(project__status=True) # base Q objkect
        slot = utils.getDashboardMilestonesTimeSlot(request)
        if 'from' in slot:
            q_objects = q_objects & Q(deadline_date__gte=slot["from"])
        if 'to' in slot:
            q_objects = q_objects & Q(deadline_date__lte=slot["to"])
            
        ms=self.queryset.filter(q_objects).order_by('deadline_date')
        
        return JsonResponse(serializers.MilestonesSerializer(ms, many=True, context={'request': request}).data, safe=False)
    
    
    