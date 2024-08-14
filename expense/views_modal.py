from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from bootstrap_modal_forms.generic import BSModalCreateView, BSModalUpdateView, BSModalDeleteView
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, reverse_lazy
from django.shortcuts import render

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.http import Http404



from . import models
from .forms import ContractModelForm, ContractExpenseModelForm, ContractTypeModelForm, ExpenseModelForm, GenericExpenseModelForm

import logging
logger = logging.getLogger("labsmanager")

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
    


class ExpenseModalView():
    class Meta:
        abstract = True
        
    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        
        exp = models.Contract_expense.objects.filter(pk= pk)
        if not exp.exists():
            exp = models.Expense.objects.filter(pk= pk)
        try:
            # Get the single item from the filtered queryset
            obj = exp.get()
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": exp.model._meta.verbose_name}
            )
        return obj

class ExpenseUpdateView(ExpenseModalView, LoginRequiredMixin, BSModalUpdateView):
    
    template_name = 'form_validate_base.html'
    success_message = 'Success: Cost TYpe was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
        
    def get_form_class(self):
        if not self.object:
            raise ImproperlyConfigured(
                    "using this class without object is prohibited"
                ) 
        if isinstance(self.object, models.Contract_expense):
            return ContractExpenseModelForm
        return ExpenseModelForm
    
class ExpenseDeleteView(ExpenseModalView, LoginRequiredMixin, BSModalDeleteView):
    template_name = 'form_delete_base.html'
    # form_class =x EmployeeModelForm
    success_url = reverse_lazy('project_index')
        
    def post(self, *args, **kwargs):
        
        self.object = self.get_object()
        self.object.delete()
        return HttpResponse("okok", status=200)
    
class ExpenseCreateView(LoginRequiredMixin, BSModalCreateView):
    template_name = 'form_base.html'
    form_class = GenericExpenseModelForm
    success_message = 'Success: Employee was updated.'
    success_url = reverse_lazy('project_index')
    label_confirm = "Confirm"
    model = models.Expense

    def get(self, request, *args, **kwargs):
        kw = self.get_form_kwargs()
        initial={} 
        
        if 'pk' in kwargs:
            initial['expense']= kwargs['pk']
        elif 'fund' in kwargs:
            initial['fund']= kwargs['fund']
        kw['initial'] = initial
        form = self.form_class(**kw)       
        
        context = {'form': form}
        return render(request, self.template_name , context)


## Launch synchronise project fund and expense

from labsmanager.views_modal import BSmodalConfirmViewMixin
from fund.models import Fund
class ConfirmSyncView(LoginRequiredMixin, BSmodalConfirmViewMixin):
    action_def = _("Syncing All singles expense and timepoint")
    
    hidden_field=['fund_id']
    
    def action(self, *args, **kwargs):
        if not "fund_id" in kwargs:
            raise ImproperlyConfigured(
                    "ConfirmSyncView's action method needs 'fund_id' paramater, none has been provided in kwargs" 
                )
        fund_id = kwargs["fund_id"]
        logger.debug(f" Start Syncing expense and timepoint for fund : {fund_id}")
        try:
            fund = Fund.objects.get(pk=fund_id)
        except:
            logger.error(f" {fund_id} not found in Fund objects")
            raise ObjectDoesNotExist(f" {fund_id} not found in Fund objects")
        
        fund.calculate_expense(force=True)
        
        return HttpResponse("Fund Synchronised", status=202)