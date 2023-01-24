from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from django import forms
from django.db.models import Q
from staff.models import TeamMate, Employee, Team

class LeaveItemModelForm(BSModalModelForm):
    class Meta:
        model = models.Leave
        fields = ['employee', 'type','start_date','end_date', 'comment', ]
        
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