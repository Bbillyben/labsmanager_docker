from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse

from . import models
from . import forms

from django.shortcuts import render

   
#### Participant
class MilestonesUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Milestones
    template_name = 'form_validate_base.html'
    form_class = forms.MilestonesModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"

# remove
class MilestonesDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Milestones
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('employee')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
class MilestonesCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = forms.MilestonesModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Milestones

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}
        if 'pk' in kwargs:
            initial['milestones']= kwargs['pk']
        elif 'project' in kwargs:
            initial['project']= kwargs['project']
        kw['initial'] = initial
        form = self.form_class(**kw)
        
        context = {'form': form}
        return render(request, self.template_name , context)
