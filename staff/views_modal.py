from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import TeamModelForm, TeamMateModelForm


# Update
class TeamUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Team
    template_name = 'form_validate_base.html'
    form_class = TeamModelForm
    success_message = 'Success: Team was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class TeamCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = TeamModelForm
    success_message = 'Success: Team was created.'
    success_url = reverse_lazy('project_index')
    
# remove
class TeamRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Team
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')
    
    
class TeamMateCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = TeamMateModelForm
    success_message = 'Success: TeamMate was created.'
    success_url = reverse_lazy('project_index')
    
    def get(self, request, *args, **kwargs):
        initial={}
        data=request.GET
        
        team_pk=data.get("team_pk", None)
        if team_pk is not None :
            initial['team']=team_pk

        
        form = self.form_class(initial=initial)
        context = {'form': form}
        return render(request, self.template_name , context)

# remove
class TeamMateRemoveView(LoginRequiredMixin, BSModalDeleteView):
    model = models.TeamMate
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee_index')