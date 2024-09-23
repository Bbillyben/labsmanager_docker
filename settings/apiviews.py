
from rest_framework import generics, status, viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from django.http import JsonResponse
from . import models, serializers
from labsmanager import serializers as labserializers
import logging
logger=logging.getLogger("labsmanager")

class UserSettingsDetail(generics.RetrieveUpdateAPIView):
    """Detail view for an individual "user setting" object.
    - User can only view / edit settings their own settings objects
    """
    lookup_field = 'key'
    queryset = models.LMUserSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def get_object(self):
        """Attempt to find a user setting object with the provided key."""
        key = self.kwargs['key']
        if key not in models.LMUserSetting.SETTINGS.keys():
            raise Exception('Not found') 

        return models.LMUserSetting.get_setting_object(key, user=self.request.user)
    
    permission_classes = (IsAuthenticated,)
    
class UserSettingsList(generics.ListAPIView):
    """API endpoint for accessing a list of user settings objects."""

    queryset = models.LMUserSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def filter_queryset(self, queryset):
        """Only list settings which apply to the current user."""
        try:
            user = self.request.user
        except AttributeError:  # pragma: no cover
            return models.LMUserSetting.objects.none()

        queryset = super().filter_queryset(queryset)

        queryset = queryset.filter(user=user)

        return queryset
    
    permission_classes = (IsAuthenticated,)
import json
class ProjectSettingsDetail(generics.RetrieveUpdateAPIView):
    """Detail view for an individual "user setting" object.
    - User can only view / edit settings their own settings objects
    """
    lookup_field = 'key'
    queryset = models.LMProjectSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def get_object(self):
        """Attempt to find a user setting object with the provided key."""
        key = self.kwargs['key']          
             
        project = self.request.data.get("project", None)
        if not project:
            try:
                # project = json.loads(list(self.request.GET.keys())[0]).get("project", None) #
                project =self.request.GET.get("project", None)
            except:
                logger.warning(f"Unable to find project setting {key}")
        
        if key not in models.LMProjectSetting.SETTINGS.keys() or not project :
            raise Exception('Not found') 

        return models.LMProjectSetting.get_setting_object(key, project=project)
   
    
    permission_classes = (IsAuthenticated,)   
from project.models import Project
class ProjectSettingsList(generics.ListAPIView):
    """API endpoint for accessing a list of user settings objects."""

    queryset = models.LMProjectSetting.objects.all()
    serializer_class = serializers.UserSettingsSerializer

    def filter_queryset(self, queryset):
        """Only list settings which apply to the current user."""
        project_id = self.request.data.get("project", None)
        try:
            project=Project.object.get(pk = project_id)
        except AttributeError:  # pragma: no cover
            return models.LMProjectSetting.objects.none()

        queryset = super().filter_queryset(queryset)

        queryset = queryset.filter(project=project)

        return queryset
    
    permission_classes = (IsAuthenticated,)    


class GlobalSettingsList(generics.ListAPIView):
    """API endpoint for accessing a list of global settings objects."""

    queryset = models.LabsManagerSetting.objects.all()
    serializer_class = serializers.GlobalSettingsSerializer
    

class GlobalSettingsDetail(generics.RetrieveUpdateAPIView):
    """Detail view for an individual "global setting" object.
    - User must have 'staff' status to view / edit
    """

    lookup_field = 'key'
    queryset = models.LabsManagerSetting.objects.all()
    serializer_class = serializers.GlobalSettingsSerializer

    def get_object(self):
        """Attempt to find a global setting object with the provided key."""
        key = self.kwargs['key']

        if key not in models.LabsManagerSetting.SETTINGS.keys():
            raise Exception('Not found') 

        return models.LabsManagerSetting.get_setting_object(key)

    permission_classes = [
        permissions.IsAuthenticated,
    ]
    
from fund import models as fund_model
from expense import models as expense_model
from leave import models as leave_model
from project.models import Institution, GenericInfoTypeProject
from infos.models import OrganizationInfosType, ContactInfoType, ContactType
from staff import models as staff_model
from django.contrib.auth import get_user_model   

class SettingListViewSet(viewsets.ModelViewSet):
    queryset = None
    serializer_class = None
    permission_classes = [permissions.IsAuthenticated]        
    filter_backends = (filters.DjangoFilterBackend,)
    
    @action(methods=['get'], detail=False, url_path='costtype', url_name='costtype')
    def costtype(self, request):
        return JsonResponse(labserializers.CostTypeSerialize_tree(fund_model.Cost_Type.objects.all(), many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=False, url_path='fundinstitution', url_name='fundinstitution')
    def fundinstitution(self, request):
        return JsonResponse(labserializers.Fund_InstitutionSerializer(fund_model.Fund_Institution.objects.all(), many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=False, url_path='contracttype', url_name='contracttype')
    def contracttype(self, request):
        return JsonResponse(labserializers.ContractTypeSerializer(expense_model.Contract_type.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='leavetype', url_name='leavetype')
    def leavetype(self, request):
        return JsonResponse(labserializers.LeaveTypeSerializer_tree(leave_model.Leave_Type.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='projectinstitution', url_name='projectinstitution')
    def projectinstitution(self, request):
        return JsonResponse(labserializers.InstitutionSerializer(Institution.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='employeetype', url_name='employeetype')
    def employeetype(self, request):
        return JsonResponse(labserializers.EmployeeTypeSerialize(staff_model.Employee_Type.objects.all(), many=True).data, safe=False)

    @action(methods=['get'], detail=False, url_path='genericinfotype', url_name='genericinfotype')
    def genericinfotype(self, request):
        return JsonResponse(labserializers.EmployeeInfoTypeIconSerialize(staff_model.GenericInfoType.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='genericinfotypeproject', url_name='genericinfotypeproject')
    def genericinfotypeproject(self, request):
        return JsonResponse(labserializers.ProjectInfoTypeIconSerialize(GenericInfoTypeProject.objects.all(), many=True).data, safe=False)

    @action(methods=['get'], detail=False, url_path='organizationinfostype', url_name='organizationinfostype')
    def organizationinfostype(self, request):
        return JsonResponse(labserializers.OrgaInfoTypeSerializer(OrganizationInfosType.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='contactinfostype', url_name='contactinfostype')
    def contactinfostype(self, request):
        return JsonResponse(labserializers.OrgaInfoTypeSerializer(ContactInfoType.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='contacttype', url_name='contacttype')
    def contacttype(self, request):
        return JsonResponse(labserializers.ContactTypeSerializer(ContactType.objects.all(), many=True).data, safe=False)
    
    
    @action(methods=['get'], detail=False, url_path='employeeuser', url_name='employeeuser')
    def employeeuser(self, request):
        usermodel = get_user_model()
        return JsonResponse(labserializers.UserEmployeeSerializer(usermodel.objects.all(), many=True).data, safe=False)