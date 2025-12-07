from django.utils.translation import gettext_lazy as _
from .models import Milestones
from django import forms
from bootstrap_modal_forms.forms import BSModalModelForm

from project.models import Project, Participant
from staff.models import Employee
from labsmanager.forms import DateInput, PercentageField

from labsmanager.mixin import SanitizeDataFormMixin

class MilestonesModelForm(SanitizeDataFormMixin, BSModalModelForm):
    quotity = PercentageField(
        label=_("Quotity(%)"),
        max_value=100,
        min_value=0,
        decimal_places=3,
        required=True,
        help_text=_("Involvment percentage")
    )
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
    
    def clean(self):
        cleaned_data = super().clean()
        status  = cleaned_data.get('status')
        quotity = cleaned_data.get('quotity') 
        if status == True : 
            cleaned_data["quotity"]=1.000
        elif quotity == 1.000:
            cleaned_data["status"]=True
        
        return cleaned_data
            
### Action form
from django.utils.safestring import mark_safe
class checkMilestonesForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        milestones = kwargs.pop('milestones', None)
        super().__init__(*args, **kwargs)
        if milestones:
            for category, mss in milestones.items():
                for ms in mss:
                    field_name = f"milestone_{ms.id}"
                    initial_value = category == "preselect"  # True si "preselect", False si autre
                    self.base_fields[field_name] = forms.BooleanField(
                        label=mark_safe(f"<strong>{ms.name}</strong> - {ms.deadline_date}"),
                        required=False,
                        initial=initial_value,
                        widget=forms.CheckboxInput(attrs={
                            'class': 'small-cb'
                        })
                    )
                    self.fields[field_name] = self.base_fields[field_name]

class delayMilestonesForm(checkMilestonesForm):
    quantity = forms.IntegerField(
        label=_('Quantity'),
        required=False,
        help_text=_("number of day to add to current date")
        
    )

class ValidateMilestonesForm(checkMilestonesForm):
    pass
                    