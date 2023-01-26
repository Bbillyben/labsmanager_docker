from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from project.models import Project
from django.utils.translation import gettext_lazy as _
from django import forms
from project.models import Project

from labsmanager.forms import DateInput

class FundItemModelForm(BSModalModelForm):
    class Meta:
        model = models.Fund_Item
        fields = ['fund', 'type','amount',]

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
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['fund'].widget = forms.HiddenInput()
            
            
class FundModelForm(BSModalModelForm):
    class Meta:
        model = models.Fund
        fields = ['project', 'funder','institution','start_date', 'end_date', 'ref','is_active',]
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
            raise ValidationError(_('Exit Date (%s) should be later than entry date (%s) ') % (self.cleaned_data['end_date'], self.cleaned_data['start_date']))
        return self.cleaned_data['end_date']
    
    def clean_is_active(self):
        if self.cleaned_data['is_active']==False and (self.cleaned_data['end_date']==None):
             raise ValidationError(_('If A Contract is turn inactive, it should have a end Dat '))
        return self.cleaned_data['is_active']