from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render
from . import models
from .forms import FundItemModelForm, FundModelForm, BudgetModelForm, CostTypeModelForm, FundInstitutionModelForm, ContributionModelForm
from expense.forms import ExpenseTimepointModelForm
from expense.models import Expense_point
    
################# FUND ITEM

class FundItemCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = FundItemModelForm
    success_message = 'Success: Fund Item was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = models.Fund_Item

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}        
        if 'pk' in kwargs:
            initial['fund_item']= kwargs['pk']
        elif 'fund' in kwargs:
            initial['fund']= kwargs['fund']
            form = self.form_class()        
        kw['initial'] = initial
        form = self.form_class(**kw)        
        context = {'form': form}
        return render(request, self.template_name , context)

class FundItemUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Fund_Item
    template_name = 'form_validate_base.html'
    form_class = FundItemModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"

class FundItemDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Fund_Item
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
################# Expense Timepoint
class ExpenseTimepointCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = ExpenseTimepointModelForm
    success_message = 'Success: Fund Item was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"
    model = Expense_point

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}  
        if 'pk' in kwargs:
            initial['expense_timepoint']= kwargs['pk']
        elif 'fund' in kwargs:
            initial['fund']= kwargs['fund']        
        kw['initial'] = initial
        form = self.form_class(**kw)        
        
        context = {'form': form}
        return render(request, self.template_name , context)  
class ExpenseTimepointUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = Expense_point
    template_name = 'form_validate_base.html'
    form_class = ExpenseTimepointModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('employee_index')
    label_confirm = "Confirm"   

from labsmanager.views_modal import BSmodalDeleteViwGenericForeingKeyMixin 
class ExpenseTimepointDeleteView(LoginRequiredMixin,BSmodalDeleteViwGenericForeingKeyMixin, BSModalDeleteView):
    model = Expense_point
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('projemployee_indexect_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
################# FUND

class FundCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = FundModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Fund

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}   
        initial={'user':request.user}
        if 'pk' in kwargs:
            initial['fund']= kwargs['pk']
        elif 'project' in kwargs:
            initial['project']= kwargs['project']
      
        kw['initial'] = initial
        form = self.form_class(**kw) 
        
        context = {'form': form}
        return render(request, self.template_name , context)

class FundUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Fund
    template_name = 'form_validate_base.html'
    form_class = FundModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"

class FundDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Fund
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
################# BUDGET
class BudgetCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = BudgetModelForm
    success_message = 'Success: Budget was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Budget

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={}        
        if 'project' in kwargs:
            initial['project']= kwargs['project']
        if 'employee' in kwargs:
            initial['employee']= kwargs['employee']

        kw['initial'] = initial
        form = self.form_class(**kw)
        context = {'form': form}
        return render(request, self.template_name , context)
    
class BudgetUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Budget
    template_name = 'form_validate_base.html'
    form_class = BudgetModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
    
class BudgetDeleteView(LoginRequiredMixin, BSModalDeleteView):
    model = models.Budget
    template_name = 'form_delete_base.html'
    # form_class = EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
################# Contribution
class ContributionCreateView(BudgetCreateView):
    form_class = ContributionModelForm
    model = models.Contribution
    
class ContributionUpdateView(BudgetUpdateView): 
    form_class = ContributionModelForm
    model = models.Contribution
    
class ContributionDeleteView(BudgetDeleteView):
    model = models.Contribution
    
############# Cost Type
class CostTypeCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = CostTypeModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Cost_Type
    
class CostTypeUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Cost_Type
    template_name = 'form_validate_base.html'
    form_class = CostTypeModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    
class FundInstitutionCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = FundInstitutionModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Fund_Institution
    
class FundInstitutionUpdateView(LoginRequiredMixin, BSModalUpdateView):
    model = models.Fund_Institution
    template_name = 'form_validate_base.html'
    form_class = FundInstitutionModelForm
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"