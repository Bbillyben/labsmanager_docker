
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
from invitations.models import Invitation
from notification.models import UserNotification
from labsmanager.mixin import LabPaginationMixin
from labsmanager.pagination import LabPagination
from django.core.exceptions import FieldError

class SettingListViewSet(LabPaginationMixin, viewsets.GenericViewSet):
    # queryset = None
    # serializer_class = None
    permission_classes = [permissions.IsAuthenticated]        
    # filter_backends = (filters.DjangoFilterBackend,)
    pagination_class = LabPagination
    
    queryset_by_action = {
        "costtype": fund_model.Cost_Type.objects.all(),
        "fundinstitution": fund_model.Fund_Institution.objects.all(),
        "contracttype": expense_model.Contract_type.objects.all(),
        "leavetype": leave_model.Leave_Type.objects.all(),
        "projectinstitution": Institution.objects.all(),
        "employeetype": staff_model.Employee_Type.objects.all(),
        "genericinfotype": staff_model.GenericInfoType.objects.all(),
        "genericinfotypeproject": GenericInfoTypeProject.objects.all(),
        "organizationinfostype": OrganizationInfosType.objects.all(),
        "contactinfostype": ContactInfoType.objects.all(),
        "contacttype": ContactType.objects.all(),
        "userinvitation": Invitation.objects.all(),
        "pendingnotification": UserNotification.objects.filter(send=None),
    }

    serializer_by_action = {
        "costtype": labserializers.CostTypeSerialize_tree,
        "fundinstitution": labserializers.Fund_InstitutionSerializer,
        "contracttype": labserializers.ContractTypeSerializer,
        "leavetype": labserializers.LeaveTypeSerializer_tree,
        "projectinstitution": labserializers.InstitutionSerializer,
        "employeetype": labserializers.EmployeeTypeSerialize,
        "genericinfotype": labserializers.EmployeeInfoTypeIconSerialize,
        "genericinfotypeproject": labserializers.ProjectInfoTypeIconSerialize,
        "organizationinfostype": labserializers.OrgaInfoTypeSerializer,
        "contactinfostype": labserializers.OrgaInfoTypeSerializer,
        "contacttype": labserializers.ContactTypeSerializer,
        "userinvitation": labserializers.InvitationSerializer,
        "pendingnotification": labserializers.UserNotificationSerializer,
    }
    ordering_fields_by_action = {
        "costtype": {
            "name": ("tree_id", "lft"),
            "short_name": ("tree_id", "lft"),
        },
        "leavetype": {
            "name": ("tree_id", "lft"),
            "short_name": ("tree_id", "lft"),
        },
    }
    def get_queryset(self):
        queryset = self.queryset_by_action.get(self.action)

        if queryset is None:
            return expense_model.Contract_type.objects.none()

        return queryset.all()

    def get_serializer_class(self):
        serializer_class = self.serializer_by_action.get(self.action)

        if serializer_class is None:
            raise AssertionError(
                f"No serializer configured for action '{self.action}'"
            )

        return serializer_class
    
    def get_ordering_fields(self, queryset):
        """
        Retourne un mapping :
        champ reçu dans la requête -> champ(s) ORM réel(s).
        """

        fields = {
            field.name: field.name
            for field in queryset.model._meta.concrete_fields
        }

        # Mapping générique éventuel du ViewSet
        fields.update(
            getattr(self, "ordering_fields", {}) or {}
        )

        # Mapping propre à l'action courante
        ordering_by_action = getattr(
            self,
            "ordering_fields_by_action",
            {},
        )

        fields.update(
            ordering_by_action.get(
                getattr(self, "action", None),
                {},
            )
        )

        return fields
    def resolve_ordering_field(self, queryset, request_name):
        mapping = self.get_ordering_fields(queryset)

        orm_fields = mapping.get(
            request_name,
            request_name.replace(".", "__"),
        )

        if isinstance(orm_fields, str):
            orm_fields = (orm_fields,)

        try:
            queryset.order_by(*orm_fields)
            return orm_fields
        except FieldError:
            return None
    def apply_ordering(self, queryset):
        ordering = self.request.query_params.get("ordering")

        if not ordering:
            return queryset

        fields = []

        for requested_field in ordering.split(","):
            requested_field = requested_field.strip()

            if not requested_field:
                continue

            descending = requested_field.startswith("-")
            request_name = requested_field.lstrip("-")

            orm_fields = self.resolve_ordering_field(
                queryset,
                request_name,
            )

            if orm_fields is None:
                continue

            for orm_field in orm_fields:
                # Pour MPTT, on conserve toujours parent avant enfant.
                if tuple(orm_fields) == ("tree_id", "lft"):
                    fields.extend([
                        "-tree_id" if descending else "tree_id",
                        "lft",
                    ])
                else:
                    fields.append(
                        f"-{orm_field}"
                        if descending
                        else orm_field
                    )

        if fields:
            return queryset.order_by(*fields)

        return queryset
    
    @action(methods=['get'], detail=False, url_path='costtype', url_name='costtype')
    def costtype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
    
    @action(methods=['get'], detail=False, url_path='fundinstitution', url_name='fundinstitution')
    def fundinstitution(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
    
    @action(methods=['get'], detail=False, url_path='contracttype', url_name='contracttype')
    def contracttype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
        
    @action(methods=['get'], detail=False, url_path='leavetype', url_name='leavetype')
    def leavetype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
        return JsonResponse(labserializers.LeaveTypeSerializer_tree(leave_model.Leave_Type.objects.all(), many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='projectinstitution', url_name='projectinstitution')
    def projectinstitution(self, request):
        return self.paginated_response(
            Institution.objects.all(), 
            serializer_class=labserializers.InstitutionSerializer,
        )
    @action(methods=['get'], detail=False, url_path='employeetype', url_name='employeetype')
    def employeetype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )

    @action(methods=['get'], detail=False, url_path='genericinfotype', url_name='genericinfotype')
    def genericinfotype(self, request):
       return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
    @action(methods=['get'], detail=False, url_path='genericinfotypeproject', url_name='genericinfotypeproject')
    def genericinfotypeproject(self, request):
       return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
    @action(methods=['get'], detail=False, url_path='organizationinfostype', url_name='organizationinfostype')
    def organizationinfostype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
        
    @action(methods=['get'], detail=False, url_path='contactinfostype', url_name='contactinfostype')
    def contactinfostype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
        
    @action(methods=['get'], detail=False, url_path='contacttype', url_name='contacttype')
    def contacttype(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )
        
    
    @action(methods=['get'], detail=False, url_path='employeeuser', url_name='employeeuser')
    def employeeuser(self, request):
        User = get_user_model()
        usermodels = User.objects.order_by('-is_active', 'username')
        return self.paginated_response(
            usermodels,
            serializer_class=labserializers.UserEmployeeSerializer,
        )
        return JsonResponse(labserializers.UserEmployeeSerializer(usermodels, many=True).data, safe=False)
    
    @action(methods=['get'], detail=False, url_path='userinvitation', url_name='userinvitation')
    def invitationsuser(self, request):
        return self.paginated_response(
            self.get_queryset(),
            serializer_class=self.get_serializer_class(),
        )

    @action(methods=['get'], detail=False, url_path='pendingnotification', url_name='pendingnotification')
    def pendingnotificationuser(self, request):
        invi = UserNotification.objects.filter(send=None)
        return JsonResponse(labserializers.UserNotificationSerializer(invi, many=True).data, safe=False)