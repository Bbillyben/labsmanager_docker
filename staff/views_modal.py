from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView, BSModalFormView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import TeamModelForm, TeamMateModelForm, EmployeeTypeModelForm,GenericInfoTypeForm, EmployeeUserModelForm, UserEmployeeModelForm

from labsmanager.mixin import CreateModalNavigateMixin

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
        initial={}
        data=request.GET
        
        team_pk=data.get("team_pk", None)
        if team_pk is not None :
            initial['team']=team_pk

        
        form = self.form_class(initial=initial)
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