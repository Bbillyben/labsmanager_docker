from collections import OrderedDict
from typing import List

from django.http import JsonResponse
from django.db import models
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import django.dispatch
from dateutil.rrule import *


from .manager import Current_date_Manager, outof_date_Manager, date_manager, focus_manager,futur_date_Manager

from datetime import date, datetime
import copy

from django_tables2 import Column, SingleTableMixin, Table

class TableViewMixin(SingleTableMixin):
    # disable pagination to retrieve all data
    # https://mattsch.com/2021/05/28/django-django_tables2-and-bootstrap-table/
    
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # build list of columns and convert it to an
        # ordered dict to retain ordering of columns
        # the dict maps from column name to its header (verbose name)
        table: Table = self.get_table()
        table_columns: List[Column] = [
            column
            for column in table.columns
        ]

        # retain ordering of columns
        columns_tuples = [(column.name, column.header) for column in table_columns]
        columns: OrderedDict[str, str] = OrderedDict(columns_tuples)

        context['columns'] = columns

        return context

    def get(self, request, *args, **kwargs):
        # trigger filtering to update the resulting queryset
        # needed in case of additional filtering being done
        response = super().get(self, request, *args, **kwargs)
        
        if 'json' in request.GET:
            table: Table = self.get_table()

            data = [
                {column.name: cell for column, cell in row.items()}
                for row in table.paginated_rows
            ]

            return JsonResponse(data, safe=False)
        else:
            return response
        

#    Cached Model Mixin and Signals
cmm_postsave = django.dispatch.Signal()
class CachedModelMixin(models.Model):
    ''' Mixin to add a dedicated signal to process cached var 
    eg : fund.signals.save_CachedModel_handler to historize vairable changes
    '''
    cached_vars = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.var_cache = {}
        for var in self.cached_vars:
            self.var_cache[var] = copy.copy(getattr(self, var))
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cmm_postsave.send(sender=self.__class__, instance=self)
    
    class Meta:
        abstract = True
                   
        
class LabsManagerBudgetMixin(models.Model):
    ''' add amount and expense variable 
    add method for calculaton
    '''
    class Meta:
        abstract = True
        
    amount=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Amount'), default=0, null=True)
    expense=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Expense'), default=0, null=True)
    
    @property
    def available(self):
        return self.amount + self.expense
    
    def get_consumption_ratio(self):
        if self.amount != 0:
            return abs(self.expense/self.amount)
        else:
            return "-"
    
    def clean_expense(self):
        if self.cleaned_data['expense']>0:
            self.cleaned_data['expense']=-self.cleaned_data['expense']
        return self.cleaned_data['expense']

class LabsManagerFocusBudgetMixin(LabsManagerBudgetMixin):
    ''' add amount_f and expense_f variable reprensenting total amount in Focus
    add method for calculaton
    '''
    class Meta:
        abstract = True
    
    amount_f=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Focus Amount'), default=0, null=True)
    expense_f=models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Focus Expense'), default=0, null=True)
      
    @property
    def available_f(self):
        return (self.amount_f or 0) + (self.expense_f or 0)
    
    def get_consumption_ratio_f(self):
        if self.amount_f != 0:
            return abs((self.expense_f or 0)/self.amount_f)
        else:
            return "-"
    
    def clean_expense_f(self):
        if self.cleaned_data['expense_f']>0:
            self.cleaned_data['expense_f']=-self.cleaned_data['expense_f']
        return self.cleaned_data['expense_f']


class LabsManagerFocusTypeMixin(models.Model):
    class Meta:
        abstract = True
    type = models.ForeignKey('fund.Cost_Type', on_delete=models.CASCADE, verbose_name=_('Type'))
    
    objects = models.Manager() 
    in_focus = focus_manager()
    
class DateMixin(models.Model):
    ''' add start and end date + manager to select current or not current items 
    
    '''
    start_date=models.DateField(null=True, blank=True, verbose_name=_('Start Date'))
    end_date=models.DateField(null=True, blank=True, verbose_name=_('End Date'))
    
        
    objects = date_manager()
    current = Current_date_Manager()
    past = outof_date_Manager()
    futur = futur_date_Manager()
    
    
    @property
    def open_days(self):
        d1=rrule(DAILY, dtstart=self.start_date, until=self.end_date, byweekday=[MO, TU, WE, TH, FR])
        d2=list(d1)
        return len(d2)
    
    def get_time_ratio(self):
        try:
            sn=date.today()
            sd = self.start_date
            se = self.end_date
            d1=sn-sd
            d2=se-sd
            r = max(min((d1.days)/(d2.days), 1), 0)
        except:
            r="-"
        return r
    
    def get_left_time_ratio(self):
        try:
            sn=date.today()
            sd = self.start_date
            se = self.end_date
            d1=se-sn
            d2=se-sd
            r = max(min((d1.days)/(d2.days), 1), 0)
        except:
            r="-"
        return r
        
        
    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=F('start_date')),
                name=_("End Date should be greater than start date"),
            )
        ]
    
class ActiveDateMixin(DateMixin):
        
    class Meta:
        abstract = True
        
    @property
    def is_active(self):
        is_a = True
        if self.start_date:
            is_a =is_a & (self.start_date <= date.today())
        if self.end_date:
            is_a =is_a & (self.end_date >= date.today())
        return is_a
    
    @classmethod
    def get_active_filter(cls):
        query = (Q(start_date=None) | Q(start_date__lte=date.today())) & (Q(end_date=None) | Q(end_date__gte=date.today()))
        return query
    
    @classmethod
    def get_inactive_filter(cls):
        query = Q(start_date__gte=date.today()) | Q(end_date__lte=date.today())
        return query


class CrumbListMixin():
    ''' add in context a list of links for the template to be display for fast switch between items
    define permission to add this list to template
    
    '''
    reverseURL=None
    crumbListQuerySet=None
    names_val=None
    id_name="id"
    crumbListPerm=() #persmission to check to send crumb list to template
    default_kwargs={} #define to add kwargs to the reverse url method
    
    class Meta:
        abstract = True
    
    def has_crumb_permission(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_staff:
            return True
        if len(self.crumbListPerm) == 0:
            return True
        for perm in self.crumbListPerm:
            if self.request.user.has_perm(perm):
                return True
        return False
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if not self.has_crumb_permission():
            return context
        
        sel=self.crumbListQuerySet.filter(~Q(pk=self.kwargs['pk'])).values() #'pk', self.names_val)
        li=[]
        for e in sel:
            n=""
            for i in self.names_val:
                n+=str(e.get(i))+" "
            kw = {'pk':e.get(self.id_name)}
            kw.update(self.default_kwargs)
            li.append([
                reverse(self.reverseURL, kwargs=kw ),
                n
                ])
            
        context['crumbs_list']=li
        return context
    
from bootstrap_modal_forms.generic import BSModalCreateView   
class CreateModalNavigateMixin(BSModalCreateView):
    '''add a url to navigate to to the response whenever the form is successfully submitted
    to be handled in the ajax call to navigate
    '''
    object_id="pk"
    success_single=""
    object=None
    def get_success_url(self, *args, **kwargs):
        if self.object is not None:
            if self.object.id:
                return reverse(self.success_single, kwargs={self.object_id:self.object.id})
        return super().get_success_url(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            self.form_valid(form)
            return JsonResponse({'navigate':self.get_success_url()})
        else:
            return self.form_invalid(form)
        
        

from django.utils.html import strip_tags
from django.utils.html import escape
from django import forms

class CleanedDataFormMixin:
    ''' Mixin class for Form to strip tags and escape textField before saviong
    to prevent xss attack'''
    def clean(self):
        cleaned_data = super().clean()

        for field_name, field in self.fields.items():
            # print(f'filed : {field_name}')
            if isinstance(field, forms.CharField):
                cleaned_data[field_name] = escape(strip_tags(cleaned_data[field_name]))
        return super().clean()
    

class IconFormMixin:
    ''' Mixin class to load specific JS for modal with FAIcon fields'''
    @property
    def media(self):
        response = super().media
        response._js_lists.clear()
        response._js_lists.append(['js/faicon_in/faicon.js'])
        response._js_lists.append(['faicon/js/list.min.js'])
        return response