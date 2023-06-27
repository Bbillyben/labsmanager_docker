from http.client import HTTPResponse
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import JsonResponse
from django.db.models import Q
# from django.views.generic import ListView
from .models import Employee, Team, TeamMate, Employee_Status, Employee_Type, GenericInfo
from .filters import EmployeeFilter
from expense.models import Contract
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.functional import cached_property
from view_breadcrumbs import BaseBreadcrumbMixin, DetailBreadcrumbMixin 
from labsmanager.mixin import TableViewMixin, CrumbListMixin

from django.urls import reverse_lazy
from .forms import EmployeeModelForm, EmployeeStatusForm,GenericInfoForm
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
# Create your views here.


class EmployeeIndexView(LoginRequiredMixin, BaseBreadcrumbMixin,TemplateView):
    template_name = 'employee/employee_base.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Employee
    crumbs = [(_("Employee"),_("employee"))]



class EmployeeView(LoginRequiredMixin, CrumbListMixin,  BaseBreadcrumbMixin ,  TemplateView):
    template_name = 'employee/employee_single.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Employee
    # for CrumbListMixin
    reverseURL="employee"
    crumbListQuerySet=Employee.objects.filter(is_active=True)
    names_val=['first_name', 'last_name']
    # crumbs = [("Employee","./",),("employees",reverse("employee"))]

    @cached_property
    def crumbs(self):
        return [(_("Employee"),"./",) ,
                (str(self.construct_crumb()) ,  ("A1","L1")),
                ]

    def construct_crumb(self):
        emp = Employee.objects.get(pk=self.kwargs['pk'])
        return emp

    def get_context_data(self, **kwargs):
        """Returns custom context data for the Employee view:
            - employee : the employee corresponding
        """
        context = super().get_context_data(**kwargs).copy()

        if not 'pk' in kwargs:
            return context

        id=kwargs.get("pk", None)
        employee = Employee.objects.filter(pk=id)
        context['employee'] = employee.first()

        # status
        status = Employee_Status.objects.filter(employee=id)
        if status:
            context['status']=status

        # teams where he is leader
        teams=Team.objects.filter(leader=id)
        if teams:
            context['team_leader']=teams

        #teams where he is participant
        participant = TeamMate.objects.filter(employee=id)
        if participant:
            context['team_part']=participant

        contracts = Contract.objects.filter(employee=id)
        if contracts:
            context['contracts']=contracts
         
        #Generic Info
        info=GenericInfo.objects.filter(employee=id)
        if info:
            context['info']=info
        # View top-level categories
        return context




###    FOR MODAL Modification EMPLOYEE

class EmployeeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = EmployeeModelForm
    success_message = 'Success: Employee was created.'
    success_url = reverse_lazy('employee_index')

# Update
class EmployeeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = Employee
    template_name = 'form_validate_base.html'
    form_class = EmployeeModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"

# remove
class EmployeeRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = Employee
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')

class EmployeeStatusCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = EmployeeStatusForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"

    def get(self, request, *args, **kwargs):
        if 'employee' in kwargs:
            form = self.form_class(initial={'employee': kwargs['employee']})
        else:
            form = self.form_class()
        
        context = {'form': form}
        return render(request, self.template_name , context)


    
class StatusUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = Employee_Status
    template_name = 'form_validate_base.html'
    form_class = EmployeeStatusForm
    success_message = 'Success: Status was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"

# remove
class StatusDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = Employee_Status
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee')
    
    def get_success_url(self):
        previous = self.request.META.get('HTTP_REFERER')
        return previous
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)


# ===================== For Infos =========================
class EmployeeInfoCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = GenericInfoForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"

    def get(self, request, *args, **kwargs):
        if 'employee' in kwargs:
            form = self.form_class(initial={'employee': kwargs['employee']})
        else:
            form = self.form_class()
        
        context = {'form': form}
        return render(request, self.template_name , context)

class EmployeeInfoUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = GenericInfo
    template_name = 'form_validate_base.html'
    form_class = GenericInfoForm
    success_message = 'Success: Info was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    
class EmployeeInfoDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = GenericInfo
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee')
    
    def get_success_url(self):
        previous = self.request.META.get('HTTP_REFERER')
        return previous
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
## Get the template for activation/ deactivation user
def get_employee_valid(request, pk):
    emp = Employee.objects.filter(pk=pk).first()
    return render(request, 'staff/employee_desc_table.html', {'employee': emp})

## Get the employee info table
def get_employee_info_table(request, pk):
    info=GenericInfo.objects.filter(employee__pk=pk)
    return render(request, 'employee/employee_info_table.html', {'infoEmployee': info})

# TEAMS views
class TeamIndexView(LoginRequiredMixin, BaseBreadcrumbMixin,TemplateView):
    template_name = 'team/team_base.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Team
    crumbs = [(_("Teams"),"teams")]
    
    

class TeamView(LoginRequiredMixin, CrumbListMixin, BaseBreadcrumbMixin ,  TemplateView):
    template_name = 'team/team_single.html'
    home_label = '<i class="fas fa-bars"></i>'
    model = Team
    # for CrumbListMixin
    reverseURL="team_single"
    crumbListQuerySet=Team.objects.all()
    names_val=['name']
    
    @cached_property
    def crumbs(self):
        return [(_("Team"),"./",) ,
                (str(self.construct_crumb()) ,  reverse("team_index" ) ),
                ]

    def construct_crumb(self):
        emp = Team.objects.get(pk=self.kwargs['pk'])
        return emp
    
    def get_context_data(self, **kwargs):
        """Returns custom context data for the Employee view:
            - employee : the employee corresponding
        """
        context = super().get_context_data(**kwargs).copy()

        if not 'pk' in kwargs:
            return context

        id=kwargs.get("pk", None)
        team = Team.objects.filter(pk=id)
        context['team'] = team.first()

        # View top-level categories
        return context
    
    
def get_team_resume(request, pk):
    team = Team.objects.filter(pk=pk).first()
    data = {'team': team}
    
    return render(request, 'team/team_desc_table.html', data)

def get_team_mate(request, pk):
    teamMate = TeamMate.objects.filter(team=pk)
    data = {'mates': teamMate}
    
    return render(request, 'team/team_mate_table.html', data)