from secrets import choice
from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from django.utils.translation import gettext_lazy as _
from django import forms
from staff.models import Employee
from project.models import Project
from labsmanager.forms import DateInput
from labsmanager.mixin import SanitizeDataFormMixin, IconFormMixin

class ProjectModelForm(SanitizeDataFormMixin, BSModalModelForm):
    allowed_tags= {""}
    class Meta:
        model = models.Project
        fields = ['name', 'start_date', 'end_date','status',]
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
        }
        
    def __init__(self, *args, **kwargs):
        super(ProjectModelForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['name'].disabled = True
            
    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('Exit Date (%(end)s) should be later than entry date (%(start)s) ') % ({'end':self.cleaned_data['end_date'], 'start': self.cleaned_data['start_date']}))
        return self.cleaned_data['end_date']

class ParticipantModelForm(BSModalModelForm):
    class Meta:
        model = models.Participant
        fields = ['project', 'employee','status','start_date', 'end_date', 'quotity',]
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
            proj = models.Project.objects.get(pk=kwargs['initial']['project'])
            if proj:
                self.base_fields['start_date'].initial = proj.start_date
                self.base_fields['end_date'].initial = proj.end_date
        else:
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=models.Project.objects.all(),
            )
        
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.base_fields['employee'].disabled = True
        else:
            self.base_fields['employee'].disabled = False
        
        # ===== Right Management
        # if ('request' in kwargs):
        #     user = kwargs['request'].user
        #     self.base_fields['project'].queryset=Project.get_instances_for_user('change', user, self.base_fields['project'].queryset)
        #     self.base_fields['employee'].queryset=Employee.get_instances_for_user('change', user, self.base_fields['employee'].queryset)
        # =====================   
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['employee'].queryset=Employee.objects.filter()
        elif('initial' in kwargs and 'project' in kwargs['initial']):
            self.fields['employee'].queryset=Employee.objects.filter(is_active=True)
             
        if instance and instance.pk:
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['project'].widget = forms.HiddenInput()
            self.fields['employee'].disabled = True
            self.fields['project'].disabled = True
        
        # ===== Right Management
        if ('request' in kwargs):
            user = kwargs['request'].user
            self.fields['project'].queryset=Project.get_instances_for_user('change', user, self.fields['project'].queryset)
            self.fields['employee'].queryset=Employee.get_instances_for_user('change', user, self.fields['employee'].queryset)
        # =====================   
            
    def clean_end_date(self):
        if( self.cleaned_data['end_date'] != None and (self.cleaned_data['start_date'] == None or self.cleaned_data['start_date'] > self.cleaned_data['end_date'])):
            raise ValidationError(_('Exit Date (%(end)s) should be later than entry date (%(start)s) ') % ({'end':self.cleaned_data['end_date'], 'start': self.cleaned_data['start_date']}))
        return self.cleaned_data['end_date']

class InstitutionModelForm(BSModalModelForm):
    class Meta:
        model = models.Institution_Participant
        fields = ['project', 'institution','status',]
        
    def __init__(self, *args, **kwargs):
        if ('initial' in kwargs and 'project' in kwargs['initial']):
            self.base_fields['project'].widget= forms.HiddenInput()
            # proj = models.Project.objects.get(pk=kwargs['initial']['project'])
            # if proj:
            #     self.base_fields['start_date'].initial = proj.start_date
            #     self.base_fields['end_date'].initial = proj.end_date
        else:
            self.base_fields['project'] = forms.ModelChoiceField(
                queryset=models.Project.objects.all(),
            )
        if ('initial' in kwargs and 'institution' in kwargs['initial']):
            self.base_fields['institution'].widget= forms.HiddenInput()
        else:
            self.base_fields['institution'] = forms.ModelChoiceField(
                queryset=models.Institution.objects.all(),
            )
            
        super().__init__(*args, **kwargs)
        # instance = getattr(self, 'instance', None)
        # if instance and instance.pk:
        #     self.fields['employee'].widget = forms.HiddenInput()
        #     self.fields['project'].widget = forms.HiddenInput()
class InstitutionModelFormDirect(SanitizeDataFormMixin, BSModalModelForm):
    class Meta:
        model = models.Institution
        fields = ['name','short_name',]
        
class GenericInfoProjectForm(SanitizeDataFormMixin, BSModalModelForm):
    allowed_tags= {""}
    class Meta:
        model = models.GenericInfoProject
        fields = ['info', 'project', 'value',]
    
    def __init__(self, *args, **kwargs): 
        
        self.base_fields['project'] = forms.ModelChoiceField(
            queryset=models.Project.objects.all(),
            widget=forms.HiddenInput
        )
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['info'].disabled = True
            
class GenericInfoTypeProjectForm(SanitizeDataFormMixin,IconFormMixin,  BSModalModelForm):
    allowed_tags= {""}
    class Meta:
        model = models.GenericInfoTypeProject
        fields = ['name', 'icon',]