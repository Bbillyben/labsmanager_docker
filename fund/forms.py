from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from project.models import Project
from staff.models import Employee
from django.utils.translation import gettext_lazy as _
from django import forms
from project.models import Project

from labsmanager.forms import DateInput
from datetime import date
from labsmanager.mixin import CleanedDataFormMixin

class FundItemModelForm(BSModalModelForm):
    class Meta:
        model = models.Fund_Item
        fields = ['value_date', 'fund', 'type','amount', 'entry_date']
        widgets = {
            'value_date': DateInput(),
            'entry_date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'fund' in kwargs['initial']):
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=models.Fund.objects.all(),
                widget=forms.HiddenInput
            )
        else:
            self.base_fields['fund'] = forms.ModelChoiceField(
                queryset=models.Fund.objects.all(),
            )
        # set today as default entrey date
        self.base_fields['entry_date'].initial = date.today()
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['fund'].widget = forms.HiddenInput()
            self.fields['type'].disabled = True
            
            
class FundModelForm(BSModalModelForm):
    class Meta:
        model = models.Fund
        fields = ['project', 'funder','institution','start_date', 'end_date', 'ref',]
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=models.Project.objects.all(),
                widget=forms.HiddenInput
            )
            proj = Project.objects.get(pk=kwargs['initial']['project'])
            if proj:
                self.base_fields['start_date'].initial = proj.start_date
                self.base_fields['end_date'].initial = proj.end_date
        else:
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=models.Project.objects.all(),
            )
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['project'].widget = forms.HiddenInput()
            self.fields['funder'].widget = forms.HiddenInput()
            self.fields['institution'].widget = forms.HiddenInput()
            
    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('Exit Date (%s) should be later than entry date (%s)') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']
    
    def clean_is_active(self):
        if self.cleaned_data['is_active']==False and (self.cleaned_data['end_date']==None):
             raise ValidationError(_('If A Contract is turn inactive, it should have a end Dat '))
        return self.cleaned_data['is_active']
    

class BudgetModelForm(BSModalModelForm):
    class Meta:
        model = models.Budget
        fields = ['fund', 'cost_type','amount','emp_type','contract_type', 'employee', 'quotity', 'desc']
        
    # def clean_contract_type(self,  *args, **kwargs): 
    #     print(self.cleaned_data)
    #     pass
        
    def __init__(self, *args, **kwargs):        
        
        self.base_fields['employee'].queryset=Employee.objects.filter(is_active=True)
        
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['fund'].queryset=models.Fund.objects.filter(project=kwargs['initial']['project'])
        else:
            self.base_fields['fund'].queryset= models.Fund.objects.all()
        
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.base_fields['employee'].disabled = True
            self.base_fields['cost_type'].queryset= models.Cost_Type.objects.get(short_name="RH").get_descendants(include_self=True)
        else:
            self.base_fields['employee'].disabled = False
            self.base_fields['cost_type'].queryset= models.Cost_Type.objects.all()
            
            
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['fund'].disabled = True
            self.fields['cost_type'].disabled = True
            
            # test if it's an employee fiche or not
            if 'type' in kwargs['request'].GET and kwargs['request'].GET['type']=="employee":
                self.fields['employee'].disabled = True
            else:
                self.fields['employee'].disabled = False
        #     self.fields['institution'].widget = forms.HiddenInput()

class ContributionModelForm(CleanedDataFormMixin, BudgetModelForm):     
    class Meta(BudgetModelForm.Meta):
        model = models.Contribution
        fields = ['fund', 'start_date', 'end_date', 'cost_type','amount','emp_type','contract_type', 'employee', 'quotity','desc']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            proj = Project.objects.get(pk=kwargs['initial']['project'])
            if proj:
                self.base_fields['start_date'].initial = proj.start_date
                self.base_fields['end_date'].initial = proj.end_date
        else:
            self.base_fields['start_date'].initial = None
            self.base_fields['end_date'].initial = None
                
        super().__init__(*args, **kwargs)
        
class CostTypeModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = models.Cost_Type
        fields = ['parent', 'short_name','name','in_focus',]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['parent'].disabled = True
            self.fields['short_name'].disabled = True
            self.fields['name'].disabled = True
        else:
            self.fields['parent'].disabled = False
            self.fields['short_name'].disabled = False
            self.fields['name'].disabled = False
            
class FundInstitutionModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = models.Fund_Institution
        fields = ['short_name','name',]
    
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     instance = getattr(self, 'instance', None)
    #     if instance and instance.pk:
    #         self.fields['short_name'].disabled = True
    #         self.fields['name'].disabled = True
    #     else:
    #         self.fields['short_name'].disabled = False
    #         self.fields['name'].disabled = False