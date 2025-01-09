from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import is_ajax
from django.core.exceptions import ValidationError

from project.models import Project
from . import models
from staff.models import Employee
from django.utils.translation import gettext_lazy as _
from django import forms
from fund.models import Cost_Type, Fund
from project.models import Participant
from datetime import date

from labsmanager.forms import DateInput
from labsmanager.mixin import SanitizeDataFormMixin
from settings.models import LabsManagerSetting
import logging
logger = logging.getLogger("labsmanager")
class ContractModelForm(BSModalModelForm):
    class Meta:
        model = models.Contract
        fields = ['employee', 'fund','start_date','end_date', 'contract_type', 'quotity','is_active','status']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        # print(f'[ContractModelForm - Init] ----------------------------------------------------------')
        # for a in args:
        #     print(f'  - args : {a} ')
        # for k, v in kwargs.items():
        #     print(f'  - {k} : {v}')
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.all().order_by('first_name'),
                widget=forms.HiddenInput
            )
        elif("data" in kwargs):
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.all().order_by('first_name'),
            )
        else:
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.filter(is_active=True).order_by('first_name'),
            )
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.filter(project=kwargs['initial']['project']),
            )

        else:
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.all(),
            )
            
        # ===== Right Management
        if ('request' in kwargs):
            user = kwargs['request'].user
            self.base_fields['fund'].queryset=Fund.get_instances_for_user('change', user, self.base_fields['fund'].queryset)
            self.base_fields['employee'].queryset=Employee.get_instances_for_user('change', user, self.base_fields['employee'].queryset)
        # =====================

        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['fund'].widget = forms.HiddenInput()
            if instance.status == "prov":
                self.fields['is_active'].widget = forms.HiddenInput()
                self.fields['contract_type'].required = False
                
            else:
                self.fields['status'].widget = forms.HiddenInput()
                self.fields['contract_type'].required = True

    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('Exit Date (%s) should be later than entry date (%s) ') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']
    
    def clean_is_active(self):
        if self.cleaned_data['is_active']==False and (self.cleaned_data['end_date']==None):
             raise ValidationError(_('If A Contract is turn inactive, it should have a end Date'))
        return self.cleaned_data['is_active']

class ExpenseModelForm(BSModalModelForm):
    class Meta:
        model = models.Contract_expense
        fields = ['expense_id', 'date', 'desc', 'type','status','amount',]
        widgets = {
            'date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        
    
    def save(self, commit=True):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            instance = super(ExpenseModelForm, self).save(commit=False)
            if commit:
                instance.save()
        else:
            instance = super(ExpenseModelForm, self).save(commit=False)
        return instance 
    
    
     
class ContractExpenseModelForm(BSModalModelForm):
    class Meta:
        model = models.Contract_expense
        fields = ['expense_id', 'contract', 'desc', 'date', 'type','status','amount',]
        widgets = {
            'date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.base_fields['type'].queryset = Cost_Type.objects.filter(is_hr=True).get_descendants(include_self=True)
        if ('initial' in kwargs and 'contract' in kwargs['initial']):
            self.base_fields['contract'] = forms.ModelChoiceField(
                queryset=models.Contract.objects.all(),
                widget=forms.HiddenInput
            )
        else:
            self.base_fields['contract'] = forms.ModelChoiceField(
                queryset=models.Contract.objects.all(),
            )
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['contract'].disabled = True #widget = forms.HiddenInput()
    
    def save(self, commit=True):
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            instance = super(ContractExpenseModelForm, self).save(commit=False)
            cont=instance.contract
            instance.fund_item = cont.fund
            if commit:
                instance.save()
        else:
            instance = super(ContractExpenseModelForm, self).save(commit=False)
        return instance
    
    
class ExpenseTimepointModelForm(BSModalModelForm):
    class Meta:
        model = models.Expense_point
        fields = ['fund', 'value_date', 'type','amount','entry_date']
        widgets = {
            'value_date': DateInput(),
            'entry_date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):
        
        if ('initial' in kwargs and 'fund' in kwargs['initial']):
            self.base_fields['fund'].widget=forms.HiddenInput()
        else:
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.all(),
            )
        # set today as default entrey date
        self.base_fields['entry_date'].initial = date.today()   
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['fund'].widget = forms.HiddenInput()
            self.fields['type'].disabled = True
            #self.fields['value_date'].disabled = True
            
            
    def clean_amount(self):
        return -abs(self.cleaned_data['amount'])
from fund.models import Fund
from django.forms.models import construct_instance
from datetime import date
class GenericExpenseModelForm(SanitizeDataFormMixin, BSModalModelForm):
    contract = forms.ModelChoiceField(
                queryset=models.Contract.objects.all(),
                blank=True,
                required=False
            )
    class Meta:
        model = models.Expense
        fields = ['expense_id', 'fund_item', 'desc', 'contract', 'date', 'type','status','amount',]
        widgets = {
            'date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        
        if ('initial' in kwargs and 'fund' in kwargs['initial']):
            self.base_fields['fund_item'] = forms.ModelChoiceField(
                queryset=Fund.objects.filter(pk=kwargs['initial']['fund']),
                initial = kwargs['initial']['fund']
                # widget=forms.HiddenInput
            )
            self.base_fields['contract'].queryset=models.Contract.objects.filter(fund=kwargs['initial']['fund'])
        else:
            self.base_fields['fund_item'] = forms.ModelChoiceField(
                queryset=Fund.objects.all(),
            )
            self.base_fields['contract'].queryset=models.Contract.objects.all()
        self.base_fields['date'].initial = date.today() 
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
    
    def clean(self, *arg, **kwargs):
        cleaned_data = super().clean()
        contract = cleaned_data['contract']
        exp_type = cleaned_data['type']
        is_hr = exp_type.is_hr
        if contract and not is_hr:
            raise ValidationError(_('Expense linked to a contract should be of type in human resources type'))
        return cleaned_data

    def save(self, commit=True):
        if self.cleaned_data['contract'] is None:
            self.instance = models.Expense()
        else:
            self.instance = models.Contract_expense()
        opts = self._meta
        try:
            self.instance = construct_instance(
                self, self.instance, opts.fields, opts.exclude
            )
        except ValidationError as e:
            self._update_errors(e)
            
        if not is_ajax(self.request.META) or self.request.POST.get('asyncUpdate') == 'True':
            instance = super(GenericExpenseModelForm, self).save(commit=False)
            if commit:
                instance.save()
        else:
            instance = super(GenericExpenseModelForm, self).save(commit=False)
        return instance
    
    
class ContractTypeModelForm(SanitizeDataFormMixin, BSModalModelForm):
    allowed_tags= {""}
    class Meta:
        model = models.Contract_type
        fields = ['name',]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['name'].disabled = True
        else:
            self.fields['name'].disabled = False
            
