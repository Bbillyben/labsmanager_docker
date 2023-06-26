from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import LeaveItemModelForm, LeaveTypeModelForm

class LeaveItemCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = LeaveItemModelForm
    success_message = 'Success: Fund Item was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Leave

    def get(self, request, *args, **kwargs):
        
        initial={}
        
        data=request.GET # or request.data or request.query_params
        
        if 'emp_pk' in kwargs:
            initial['employee']=kwargs['emp_pk']
        
        
        team = data.get('team', None)
        if team is not None and team.isdigit():
            initial['team']=team
            
        employee = data.get('employee', None)
        if employee is not None:
            initial['employee']=employee
        
        start_date=data.get("start_date", None)
        if start_date is not None:
            d=start_date.split("T")
            start_date=d[0]
            initial['start_date']=start_date
            if d[1][0:2] == "12":
                initial['start_period']="MI"
        
        end_date=data.get("end_date", None)
        if end_date is not None:
            d=end_date.split("T")
            initial['end_date']=d[0]
            if d[1][0:2] == "12":
                initial['end_period']="MI"

        
        form = self.form_class(initial=initial)
        context = {'form': form}
        return render(request, self.template_name , context)
    
    
class LeaveItemUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Leave
    template_name = 'form_validate_base.html'
    form_class = LeaveItemModelForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class LeaveItemDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Leave
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
    
class LeaveTypeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = LeaveTypeModelForm
    success_message = 'Success: Fund Item was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Leave_Type
    
class LeaveTypeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Leave_Type
    template_name = 'form_validate_base.html'
    form_class = LeaveTypeModelForm
    success_message = 'Success: Leave was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"