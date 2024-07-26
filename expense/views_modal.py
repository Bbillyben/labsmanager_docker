from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import ContractModelForm, ContractExpenseModelForm, ContractTypeModelForm


class ContractCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = ContractModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Contract

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={} 
        
        if 'pk' in kwargs:
            initial['contract']= kwargs['pk']
        elif 'employee' in kwargs:
            initial['employee']= kwargs['employee']
        elif 'project' in kwargs:
            initial['project']= kwargs['project']
        
        kw['initial'] = initial
        form = self.form_class(**kw)      
        
        context = {'form': form}
        return render(request, self.template_name , context)
    
    
class ContractUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Contract
    template_name = 'form_validate_base.html'
    form_class = ContractModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class ContractDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Contract
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
    
    
class ContractExpenseCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = ContractExpenseModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Contract_expense

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={} 
        
        if 'pk' in kwargs:
            initial['contract']= kwargs['pk']
        elif 'contract' in kwargs:
            initial['contract']= kwargs['contract']
        kw['initial'] = initial
        form = self.form_class(**kw)       
        
        context = {'form': form}
        return render(request, self.template_name , context)

class ContractExpenseUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Contract_expense
    template_name = 'form_validate_base.html'
    form_class = ContractExpenseModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class ContractExpenseDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Contract_expense
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    

class ContractTypeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = ContractTypeModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Contract_type
    
class ContractTypeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Contract_type
    template_name = 'form_validate_base.html'
    form_class = ContractTypeModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"