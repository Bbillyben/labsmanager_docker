from collections import OrderedDict
from typing import List

from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db import models
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db.models import Q, F, Value, Case, When, BooleanField
import django.dispatch
from django.contrib import messages
from dateutil.rrule import *
from django.core.exceptions import FieldError

from .manager import Current_date_Manager, outof_date_Manager, date_manager, focus_manager,futur_date_Manager

from datetime import date, datetime
import copy
import logging
logger=logging.getLogger("labsmanager")

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
            self.var_cache[var] = copy.copy(getattr(self, var, None))
    class Meta:
        abstract = True
                   
            
class CachedModelDispatchMixin(CachedModelMixin):
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
    time_object = date_manager()
    
    
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
    
    def get_crumbListQuerySet(self):
        return self.crumbListQuerySet
    
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
from bootstrap_modal_forms.mixins import is_ajax   


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
        
    def form_valid(self, form):
        isAjaxRequest = is_ajax(self.request.META)
        asyncUpdate = self.request.POST.get('asyncUpdate') == 'True'

        if isAjaxRequest:
            if asyncUpdate:
                self.object = form.save()
            return HttpResponse(status=204)

        self.object = form.save()
        messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())  

from django import forms
import nh3
class SanitizeDataFormMixin:
    ''' Mixin class for Form to strip tags and escape textField before saving
    to prevent xss attack
    https://nh3.readthedocs.io/en/latest/
    '''
    
    allowed_tags=None
    
    def clean(self):
        cleaned_data = super().clean()

        for field_name, field in self.fields.items():
            # print(f'filed : {field_name}')
            if (isinstance(field, forms.CharField) or isinstance(field, forms.Textarea)) and not(cleaned_data[field_name] is None):
                cleaned_data[field_name] = nh3.clean(cleaned_data[field_name], self.allowed_tags) #escape(strip_tags(cleaned_data[field_name]))
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


class TimeStampMixin(models.Model):
    ''' Mixin class to create date field for cretaion and update '''
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



# ==========================  Right Management Mixin for models 
# to provide list of instance for models
from settings.models import LabsManagerSetting
class RightsCheckerMixin():
    class Meta:
        abstract=True
        
    perms_auth=('view', 'change', 'add', 'delete')
    
    @classmethod
    def get_project_modder(cls, perm=None):
        if perm.lower() not in cls.perms_auth:
            logger.error(f"'{perm}' permission is not valid")
            return None
        # if perm == 'view':
        #     return None 
        setting = LabsManagerSetting.get_setting("CO_LEADER_CAN_EDIT_PROJECT")
        emp_stat = {"l", "cl"} if setting else {"l"}
        return emp_stat
    
    @classmethod
    def get_perm_string(cls, perm):
        if perm.lower() not in cls.perms_auth:
            logger.error(f"'{perm}' permission is not valid")
            return None
        perm_str = cls._meta.app_label + '.'+perm+"_"+cls._meta.model_name
        return perm_str
    
    @classmethod
    def get_instances_for_user(cls, perm, user, queryset=None):
        '''
        This method to be overriden to add the layer of object layer permission, here only global right layer
        '''
        if perm.lower() not in cls.perms_auth:
            logger.error(f"{perm} permission is not valid")
            return cls.objects.none()
        if not queryset:
            queryset = cls.objects.all() 
        perm_str = cls._meta.app_label + '.'+perm+"_"+cls._meta.model_name
        if user.has_perm(perm_str):
            return queryset
        return cls.objects.none()
    
    @classmethod
    def annotate_queryset(cls, queryset, user, perm):
        perm_str = cls.get_perm_string(perm)
        if not perm_str:
            return queryset.annotate(has_perm=Value(False))
        if user.has_perm(perm_str):
            return queryset.annotate(has_perm=Value(True))
        
        qset_right=[item.pk for item in queryset if user.has_perm(perm_str, item)]
        queryset = queryset.annotate(
                        has_perm=Case(
                            When(pk__in=qset_right, then=Value(True)),
                            default=Value(False),
                            output_field=BooleanField()
                        )
                    )
        return queryset
        # =======================
        
        
from labsmanager.pagination import LabPagination
from rest_framework.response import Response
from django.core.exceptions import FieldDoesNotExist
from rest_framework.response import Response

from django.db.models import Q
from rest_framework.response import Response

from rest_framework import serializers

class LabPaginationMixin:
    pagination_class = LabPagination
    search_fields = None
    extra_search_fields = []
    extra_search_fields_by_action = {}
    ordering_fields = None
    ordering_fields_by_action = {}
    
    def get_serializer_instance(self, serializer_class=None, *args, **kwargs):
        kwargs.setdefault("context", self.get_serializer_context())

        if serializer_class is None:
            return self.get_serializer(*args, **kwargs)

        if isinstance(serializer_class, type):
            return serializer_class(*args, **kwargs)

        return serializer_class
    def is_valid_search_field(self, queryset, field_path):
        """
        Vérifie qu'un chemin comme :
        employee__last_name
        correspond bien à un champ ou une relation du modèle.
        """

        model = queryset.model

        for part in field_path.split("__"):
            try:
                model_field = model._meta.get_field(part)
            except FieldDoesNotExist:
                return False

            if model_field.is_relation:
                model = model_field.related_model
            else:
                model = None

        return True
    
    def get_extra_search_fields(self):
        action = getattr(self, "action", None)

        fields_by_action = (
            getattr(self, "extra_search_fields_by_action", {})
            or {}
        )

        # Si l'action possède une configuration spécifique,
        # elle remplace les champs généraux.
        if action in fields_by_action:
            return list(fields_by_action[action])

        return list(
            getattr(self, "extra_search_fields", ())
            or ()
        )
    
    def get_search_fields(self, queryset, serializer_class=None):
        fields = []

        serializer = self.get_serializer_instance(
            serializer_class
        )

        for name, field in serializer.fields.items():
            if isinstance(field, (
                serializers.CharField,
                serializers.EmailField,
                serializers.SlugField,
            )):
                source = field.source or name

                if (
                    source != "*"
                    and "." not in source
                    and self.is_valid_search_field(queryset, source)
                ):
                    fields.append(source)

        for field in self.get_extra_search_fields():
            if self.is_valid_search_field(queryset, field):
                fields.append(field)

        return list(dict.fromkeys(fields))

    def apply_search(self, queryset, serializer_class=None):
        search = self.request.query_params.get("search")

        if not search:
            return queryset

        query = Q()

        for field in self.get_search_fields(queryset, serializer_class):
            query |= Q(**{f"{field}__icontains": search})

        if not query.children:
            return queryset

        return queryset.filter(query).distinct()
    
    def get_ordering_fields(self, queryset):
        """
        Retourne un mapping :
        champ reçu dans la requête -> chemin ORM réel.
        """

        fields = {
            field.name: field.name
            for field in queryset.model._meta.concrete_fields
        }

        # Mapping général du ViewSet
        fields.update(
            getattr(self, "ordering_fields", {}) or {}
        )

        # Mapping spécifique à l'action
        fields_by_action = getattr(
            self,
            "ordering_fields_by_action",
            {},
        ) or {}

        fields.update(
            fields_by_action.get(
                getattr(self, "action", None),
                {},
            )
        )

        return fields
    
    def resolve_ordering_field(self, queryset, request_name):
        mapping = self.get_ordering_fields(queryset)

        orm_field = mapping.get(
            request_name,
            request_name.replace(".", "__")
        )

        try:
            queryset.order_by(orm_field)
            return orm_field
        except FieldError:
            return None

    def apply_ordering(self, queryset):
        ordering = self.request.query_params.get("ordering")

        if not ordering:
            return queryset

        fields = []

        for requested_field in ordering.split(","):
            requested_field = requested_field.strip()

            if not requested_field:
                continue

            descending = requested_field.startswith("-")
            request_name = requested_field.lstrip("-")

            # Mapping explicite prioritaire
            orm_field = self.resolve_ordering_field(queryset, request_name)

            if orm_field is None:
                continue

            fields.append(
                f"-{orm_field}" if descending else orm_field
            )

        if fields:
            return queryset.order_by(*fields)

        return queryset

    def prepare_queryset(self, queryset, serializer_class=None):
        queryset = self.apply_search(queryset, serializer_class)
        queryset = self.apply_ordering(queryset)
        return queryset

    def paginated_response(self, queryset, serializer_class=None, many=True):
        queryset = self.prepare_queryset(
            queryset,
            serializer_class=serializer_class,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(
            queryset,
            self.request,
            view=self,
        )

        objects = page if page is not None else queryset

        serializer = self.get_serializer_instance(
            serializer_class,
            objects,
            many=many,
        )

        if page is not None:
            return paginator.get_paginated_response(serializer.data)

        return Response(serializer.data)