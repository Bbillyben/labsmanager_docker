from bootstrap_modal_forms.forms import BSModalModelForm
from django.core.exceptions import ValidationError
from . import models
from django import forms


class LeaveItemModelForm(BSModalModelForm):
    class Meta:
        model = models.Leave
        fields = ['employee', 'type','start_date','end_date', 'comment', ]
        
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['employee'].widget.attrs['disabled'] = True
            self.fields['type'].widget.attrs['disabled'] = True
        if ('initial' in kwargs and 'employee' in kwargs['initial']):
            self.fields['employee'].widget.attrs['disabled'] = True