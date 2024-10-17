
from .models import Milestones
from django import forms
from bootstrap_modal_forms.forms import BSModalModelForm

from project.models import Project, Participant
from staff.models import Employee
from labsmanager.forms import DateInput

from labsmanager.mixin import SanitizeDataFormMixin

class MilestonesModelForm(SanitizeDataFormMixin, BSModalModelForm):
    class Meta:
        model = Milestones
        fields = ['project', 'name','desc','deadline_date', 'type', 'quotity', 'status',
                  'employee',
                  ]
        widgets = {
            'deadline_date': DateInput(),
        }
    
    def __init__(self, *args, **kwargs):        
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=Project.objects.all(),
                widget=forms.HiddenInput
            )
            # proj = Project.objects.get(pk=kwargs['initial']['project'])
            project_part = Participant.objects.filter(project__pk=kwargs['initial']['project']).values('employee')
            self.base_fields['employee'].queryset = Employee.objects.filter(pk__in=project_part, is_active=True)
        else:
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=Project.objects.all(),
            )
            self.base_fields['employee'].queryset = Employee.objects.filter(is_active=True)
            
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        
        if instance and instance.pk:
            self.fields['project'].widget = forms.HiddenInput()
            project_part = Participant.objects.filter(project__pk=instance.project.pk).values('employee')
            self.fields['employee'].queryset = Employee.objects.filter(pk__in=project_part, is_active=True)