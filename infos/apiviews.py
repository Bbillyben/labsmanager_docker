from django.http import JsonResponse
from django.apps import apps
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, F, ExpressionWrapper, fields
from django.db.models.functions import Cast, Coalesce, Now, Extract, Abs
from datetime import datetime

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from labsmanager import serializers 

from django.contrib.contenttypes.models import ContentType

from .models import OrganizationInfos, Contact
from project.models import Project, Institution, Institution_Participant
from fund.models import Fund_Institution, Fund
from expense.models import Contract

class organisationViewSet(viewsets.ViewSet):
    queryset = OrganizationInfos.objects.all()
    serializer_class = serializers.OrganizationInfoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(methods=['get'], detail=False, url_path='(?P<app>[^/.]+)/(?P<model>[^/.]+)/(?P<id>[0-9]+)', url_name='orga_info')
    def get_orga_info(self, request, app, model, id):
        ct = ContentType.objects.get(app_label=app, model=model)
        info = OrganizationInfos.objects.filter(content_type = ct, object_id = id)
        return JsonResponse(serializers.OrganizationInfoSerializer(info, many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='(?P<app>[^/.]+)/(?P<model>[^/.]+)/(?P<id>[0-9]+)/project', url_name='orga_project')
    def get_orga_project(self, request, app, model, id):
        
        model_class = apps.get_model(app_label=app, model_name=model)
        orga = get_object_or_404(model_class, pk=id)
        
        if model_class == Institution:
            ip1 = Institution_Participant.objects.filter(institution=orga).values('project')
            ip2 = Fund.objects.filter(institution=orga).values('project')
            ip= ip1.union(ip2)
        elif model_class == Fund_Institution:
            ip = Fund.objects.filter(funder=orga).values('project')
        
        proj = Project.objects.filter(pk__in=ip) 
        
        
        ###   Filters
        params = request.GET
        status = params.get('status', None)
        if status:
            proj = proj.filter(status=status)
        pname = params.get('project_name', None)
        if pname:
            proj = proj.filter(name__icontains=pname)
        return JsonResponse(serializers.ProjectFullSerializer(proj, many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='(?P<app>[^/.]+)/(?P<model>[^/.]+)/(?P<id>[0-9]+)/contact', url_name='orga_contact')
    def get_orga_contact(self, request, app, model, id):
        ct = ContentType.objects.get(app_label=app, model=model)
        info = Contact.objects.filter(content_type = ct, object_id = id).order_by('type__name')
        
        return JsonResponse(serializers.ContactSerializer(info, many=True).data, safe=False)

    @action(methods=['get'], detail=False, url_path='(?P<app>[^/.]+)/(?P<model>[^/.]+)/(?P<id>[0-9]+)/contract', url_name='orga_contract')
    def get_orga_contract(self, request, app, model, id):
        from expense.apiviews import ContractViewSet
     
        _mutable = request.query_params._mutable
        request.query_params._mutable = True

        if model == 'institution':
            request.query_params.update({'institution_name':id})
        elif model == 'fund_institution':
            request.query_params.update({'funder':id})
        # set mutable flag back
        request.query_params._mutable = _mutable      
        
        cvs = ContractViewSet()
        cvs.request = request
        
        qs = cvs.filter_queryset(cvs.get_queryset())
        
        return JsonResponse(serializers.ContractSerializer(qs, many=True).data, safe=False)
        
    