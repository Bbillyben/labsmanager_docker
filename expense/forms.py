from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.utils import is_ajax
from django.core.exceptions import ValidationError

from project.models import Project
from . import models
from staff.models import Employee
from django.utils.translation import gettext_lazy as _
from django import forms
from fund.models import Cost_Type, Fund

from datetime import date

from labsmanager.forms import DateInput

class ContractModelForm(BSModalModelForm):
    class Meta:
        model = models.Contract
        fields = ['employee', 'fund','start_date','end_date', 'contract_type', 'quotity','is_active',]
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.all().order_by('first_name'),
                widget=forms.HiddenInput
            )
        else:
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.all().order_by('first_name'),
            )
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.filter(project=kwargs['initial']['project']),
            )

        else:
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=Fund.objects.all(),
            )
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['fund'].widget = forms.HiddenInput()

    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('Exit Date (%s) should be later than entry date (%s) ') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']
    
    def clean_is_active(self):
        if self.cleaned_data['is_active']==False and (self.cleaned_data['end_date']==None):
             raise ValidationError(_('If A Contract is turn inactive, it should have a end Date'))
        return self.cleaned_data['is_active']
    
class ContractExpenseModelForm(BSModalModelForm):
    class Meta:
        model = models.Contract_expense
        fields = ['contract', 'date', 'type','status','amount',]
        widgets = {
            'date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.base_fields['type'].queryset = Cost_Type.objects.filter(short_name__startswith='RH')
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
            self.fields['contract'].widget = forms.HiddenInput()
    
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

class ContractTypeModelForm(BSModalModelForm):
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