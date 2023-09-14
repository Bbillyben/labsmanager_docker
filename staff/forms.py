from csv import field_size_limit
from traceback import format_tb
from django import forms
from .models import Employee, TeamMate, Employee_Status, Team,GenericInfoType, GenericInfo, Employee_Type
from django.contrib.auth.models import User
from django.db.models import Q
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from labsmanager.forms import DateInput
from django.contrib.auth import get_user_model

from labsmanager.mixin import CleanedDataFormMixin

class TeamMateForm(forms.ModelForm):
    model = TeamMate
    fields = [
        "team",
        "employee",
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'instance' in kwargs:
            teamMate= kwargs['instance']
            empInTeam = TeamMate.objects.filter(team=teamMate.team).values_list('employee')
            usersU =Employee.objects.filter(~Q(user__pk=teamMate.team.leader.user.pk))
            self.fields['employee'].queryset = usersU


class EmployeeModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'birth_date', 'entry_date', 'exit_date', 'email','is_active',]
        widgets = {
            'birth_date': DateInput(),
            'entry_date': DateInput(),
            'exit_date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super(EmployeeModelForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['first_name'].disabled = True
            self.fields['last_name'].disabled = True
            
    def clean_exit_date(self):
        if( self.cleaned_data['exit_date'] != None and self.cleaned_data['entry_date'] > self.cleaned_data['exit_date']):
            raise ValidationError(_('Exit Date (%(end)s) should be later than entry date (%(start)s) ') % ({'end':self.cleaned_data['exit_date'], 'start': self.cleaned_data['entry_date']}))
        return self.cleaned_data['exit_date']

class EmployeeUserModelForm(BSModalModelForm):
    class Meta:
        model = Employee
        fields = ['user']
        
    def __init__(self, *args, **kwargs):
        super(EmployeeUserModelForm, self).__init__(*args, **kwargs)
        userModel = get_user_model()
        inEmp = Employee.objects.exclude(user=None).values('user')
        self.fields['user'].queryset = userModel.objects.exclude(pk__in=inEmp)

class UserEmployeeModelForm(BSModalForm):
    employee= forms.ModelChoiceField (queryset=Employee.objects.filter(is_active = True, user=None),  required=False, blank=True)
    class Meta:
        fields = ['employee']
    
class EmployeeStatusForm(BSModalModelForm):
    class Meta:
        model = Employee_Status
        fields = ['type', 'start_date', 'end_date', 'is_contractual', 'employee']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs): 
        
        self.base_fields['employee'] = forms.ModelChoiceField(
            queryset=Employee.objects.all(),
            widget=forms.HiddenInput
        )
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['type'].disabled = True
    
    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('End Date (%s) should be later than start date (%s) ') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']



class TeamModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = Team
        fields = ['name', 'leader',]

        
class TeamMateModelForm(BSModalModelForm):
    class Meta:
        model = TeamMate
        fields = ['team', 'employee','start_date','end_date']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'team' in kwargs['initial'] and not 'is_update' in kwargs):
            team_id=kwargs['initial']['team']
            mateInTeam=TeamMate.objects.filter(team=team_id).values('employee')
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.filter(~Q(pk__in=mateInTeam)),
            )
        else:
             self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.all(),
            )
            
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['team'].widget.attrs['disabled'] = True
            self.fields['employee'].widget.attrs['disabled'] = True
        if ('initial' in kwargs and 'team' in kwargs['initial']):
            self.fields['team'].widget.attrs['disabled'] = True
            
class GenericInfoForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = GenericInfo
        fields = ['info', 'employee', 'value',]
    
    def __init__(self, *args, **kwargs): 
        
        self.base_fields['employee'] = forms.ModelChoiceField(
            queryset=Employee.objects.all(),
            widget=forms.HiddenInput
        )
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['info'].disabled = True
            
class EmployeeTypeModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = Employee_Type
        fields = ['name','shortname',]
        
class GenericInfoTypeForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = GenericInfoType
        fields = ['name', 'icon',]

    @property
    def media(self):
        response = super().media
        response._js_lists.clear()
        response._js_lists.append(['js/faicon_in/list.min.js'])
        response._js_lists.append(['js/faicon_in/faicon.js'])
        return response
    