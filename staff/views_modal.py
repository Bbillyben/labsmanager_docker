from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import TeamModelForm, TeamMateModelForm, EmployeeTypeModelForm,GenericInfoTypeForm, EmployeeUserModelForm, UserEmployeeModelForm, EmployeeSuperiorForm,EmployeeSubordinateForm

from labsmanager.mixin import CreateModalNavigateMixin
from labsmanager.views_modal import BSmodalDeleteViwGenericForeingKeyMixin

import logging
logger = logging.getLogger("labsmanager")
# Update
class TeamUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Team
    template_name = 'form_validate_base.html'
    form_class = TeamModelForm
    success_message = 'Success: Team was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class TeamCreateView(LoginRequiredMixin, CreateModalNavigateMixin):
    template_name = 'form_base.html'
    form_class = TeamModelForm
    success_message = 'Success: Team was created.'
    success_url = reverse_lazy('team_index')
    
    success_single = 'team_single'
    
    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     if not self.request.user.has_perm("staff.change_team"):
    #         try:
    #             emp = Employee.objects.get(user= self.request.user)
    #             instance.leader = emp
    #         except Exception as e:
    #             logger.debug(f"Unable to create Project Leader from user {self.request.user} for project : {self.object}")
    #             logger.debug(f" ERROR : {e}")
    #     # Appliquer ici des modifications personnalisées à l'instance
    #     if commit:
    #         instance.save()
    #     return instance
    
# remove
class TeamRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Team
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('team_index')
    
    
class TeamMateCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = TeamMateModelForm
    success_message = 'Success: TeamMate was created.'
    success_url = reverse_lazy('team_index')
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={} 
        data=request.GET
        
        team_pk=data.get("team_pk", None)
        if team_pk is not None :
            initial['team']=team_pk

        
        kw['initial'] = initial
        form = self.form_class(**kw)
        context = {'form': form}
        return render(request, self.template_name , context)

class TeamMateUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.TeamMate
    template_name = 'form_validate_base.html'
    form_class = TeamMateModelForm
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')
    
    def get_context_data(self, **kwargs):
        self.extra_context={'is_update':True}
        return super().get_context_data(**kwargs)
    
    
# remove
class TeamMateRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.TeamMate
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')
    
class EmployeeTypeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = EmployeeTypeModelForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Employee_Type
     
class EmployeeTypeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Employee_Type    
    template_name = 'form_validate_base.html'
    form_class = EmployeeTypeModelForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    

class EmployeeUserUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Employee  
    template_name = 'form_validate_base.html'
    form_class = EmployeeUserModelForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"


from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth import get_user_model
from staff.models import Employee
class UserEmployeeUpdateView(LoginRequiredMixin, BSModalFormView):
    template_name = 'form_validate_base.html'
    form_class = UserEmployeeModelForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"    
    
    
    def post(self, request, *args, **kwargs):
        
        if not 'pk' in kwargs:
            raise ObjectDoesNotExist("User Pk not in post request")
        try:
            user = get_user_model().objects.get(pk=kwargs['pk'])
        except:
             raise ObjectDoesNotExist(f"User for pk :{kwargs['pk']} not found")
        if not 'employee' in request.POST:
            raise ObjectDoesNotExist(f"No employee in POST request : {request.POST}")
        
        ## erase previous user's employee
        try:
            emp = Employee.objects.get(user = user)
            emp.user= None
            emp.save()
        except:
            pass

        if request.POST['employee'] != '':
            try:
                emp = Employee.objects.get(pk=request.POST['employee'])
                emp.user = user
                emp.save()
            except:
                raise ObjectDoesNotExist(f"Employee for pk :{request.POST['employee']} not found")
            
        
        
        return HttpResponse("Item Saved")
    
class GenericInfoTypeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = GenericInfoTypeForm
    success_message = 'Success: Project was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.GenericInfoType
    
    
class GenericInfoTypeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.GenericInfoType    
    template_name = 'form_validate_base.html'
    form_class = GenericInfoTypeForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
    
class EmployeeSuperiorCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = EmployeeSuperiorForm
    success_message = 'Success: Employee  was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Employee_Superior
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'employee' in kwargs:
            initial['employee']= kwargs['employee']

        kw['initial'] = initial
        form = self.form_class(**kw)
        
        context = {'form': form}
        return render(request, self.template_name , context)
class EmployeeSubordinateCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = EmployeeSubordinateForm
    success_message = 'Success: Employee  was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Employee_Superior
    
    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}        
        if 'employee' in kwargs:
            initial['superior']= kwargs['employee']
            form = self.form_class(initial={'superior': kwargs['employee']})
        kw['initial'] = initial
        form = self.form_class(**kw)
        
        context = {'form': form}
        return render(request, self.template_name , context)
    
class EmployeeSuperiorUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Employee_Superior    
    template_name = 'form_validate_base.html'
    form_class = EmployeeSuperiorForm
    success_message = 'Success: EMployee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    
class EmployeeSuperiorDeleteView(LoginRequiredMixin, BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = models.Employee_Superior
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')