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
        # print("[ ContractCreateView ] "+str(kwargs))
        if 'pk' in kwargs:
            form = self.form_class(initial={'contract': kwargs['pk'], 'user':request.user})
        elif 'employee' in kwargs:
            form = self.form_class(initial={'employee': kwargs['employee'], 'user':request.user})
        elif 'project' in kwargs:
            form = self.form_class(initial={'project': kwargs['project'], 'user':request.user})
        else:
            form = self.form_class(initial={'user':request.user})        
        
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
        # print("[ ContractCreateView ] "+str(kwargs))
        if 'pk' in kwargs:
            form = self.form_class(initial={'contract': kwargs['pk']})
        elif 'contract' in kwargs:
            form = self.form_class(initial={'contract': kwargs['contract']})
        else:
            form = self.form_class()        
        
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