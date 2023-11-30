from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from django import forms
from django.db.models import Q
from staff.models import TeamMate, Employee, Team

from labsmanager.forms import DateInput,ColorInput
from labsmanager.mixin import CleanedDataFormMixin
class LeaveItemModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = models.Leave
        fields = ['employee', 'type','start_date','start_period', 'end_date', 'end_period', 'comment', ]
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
    def __init__(self, *args, **kwargs):
        
        
        
        if ('initial' in kwargs and 'team' in kwargs['initial']):
            team_id=kwargs['initial']['team']
            lead=Team.objects.filter(pk=team_id).values('leader')
            mateInTeam=TeamMate.objects.filter(team=team_id).values('employee')
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.filter((Q(pk__in=lead) | Q(pk__in=mateInTeam)) & Q(is_active=True)  ),
            )
        else:
            self.base_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.filter(is_active=True),
            )
            
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['employee'].widget.attrs['disabled'] = True
            self.fields['type'].widget.attrs['disabled'] = True
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.fields['employee'].widget.attrs['disabled'] = True
    
class LeaveTypeModelForm(CleanedDataFormMixin, BSModalModelForm):
    class Meta:
        model = models.Leave_Type
        fields = ['parent','name','short_name','color',]
    
    color = forms.CharField(
        widget = ColorInput,
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['short_name'].disabled = True
            self.fields['name'].disabled = True
        else:
            self.fields['short_name'].disabled = False
            self.fields['name'].disabled = False