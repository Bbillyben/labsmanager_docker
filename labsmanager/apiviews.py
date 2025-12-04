from http.client import HTTPResponse
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.db.models import Q

from project.models import Participant, Project
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from . import serializers  # UserSerializer, GroupSerializer, EmployeeSerialize, EmployeeStatusSerialize, ContractEmployeeSerializer, TeamSerializer, ParticipantSerializer, ProjectSerializer
from staff.models import Employee, Employee_Status, Team, TeamMate
from expense.models import Expense_point, Contract, Contract_expense
from fund.models import Fund, Fund_Item

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from dashboard import utils
from labsmanager.utils import str2bool
from staff.filters import EmployeeFilter
from expense.filters import ContractFilter

from . import lab_version
from .serializers import EmployeeSerialize_Min

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Si ?me=true dans l'URL, retourne uniquement l'utilisateur connecté
        if self.request.query_params.get("me") == "true":
            return User.objects.filter(pk=self.request.user.pk)
        return super().get_queryset()

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    
    
## for Hub Data View

    


# labmanager/api/views.py
class HubDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Permissions
        perms = {
            "common": {
                "employee_list": user.has_perm("common.employee_list"),
                "team_list": user.has_perm("common.team_list"),
                "display_infos": user.has_perm("common.display_infos"),
                "display_calendar": user.has_perm("common.display_calendar"),
                "display_dashboard": user.has_perm("common.display_dashboard"),
                "contract_list": user.has_perm("common.contract_list"),
                "project_list": user.has_perm("common.project_list"),
            },
            "staff": {
                "view_employee": user.has_perm("staff.view_employee"),
                "view_team": user.has_perm("staff.view_team"),
                "view_project": user.has_perm("project.view_project"),
            },
            "expense": {
                "view_contract": user.has_perm("expense.view_contract"),
            },
            "leave": {
                "view_leave": user.has_perm("leave.view_leave"),
            }
        }

        # Variables lab_version
        variables = {name: getattr(lab_version, name) 
                     for name in dir(lab_version) 
                     if not name.startswith("__") and not callable(getattr(lab_version, name))}
        
        if user.is_authenticated:
            from staff.models import Employee
            emp = Employee.objects.filter(user=request.user)
            if emp:
                user.employee = emp.first()
        ## color theme for user
        from labsmanager.themes import LabTheme
        from settings.models import LMUserSetting
        
        ctName = LMUserSetting.get_setting("LAB_THEME", user=user)
        ct = LabTheme.get_theme(ctName)
        color_theme_css = f"/css/color-themes/{ct}.css"
        
        
        data = {
            "user": {
                "username": user.username,
                "is_staff": user.is_staff,
                "employee":EmployeeSerialize_Min(user.employee).data,
                "is_authenticated":user.is_authenticated,
                 "color_theme": color_theme_css,
                
            },
            "perms": perms,
            "LABSMANAGER_VERSION": variables.get("LABSMANAGER_VERSION", ""),
        }

        return Response(data)

    
