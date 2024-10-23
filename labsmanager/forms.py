from django.forms import  DateInput, BooleanField, CharField, HiddenInput
from django.forms.widgets import Input, TextInput
from django.utils.translation import gettext_lazy as _

class DateInput(DateInput):
    input_type = 'date'
    
    def __init__(self, attrs=None, format=None):
        super().__init__(attrs)
        self.format = format or None
        
    def format_value(self, value):
        return value

class ColorInput(TextInput):
    input_type = 'color'
    
    # def __init__(self, attrs=None, format=None):
    #     super().__init__(attrs)
    #     self.format = format or None
        
    # def format_value(self, value):
    #     return value

from bootstrap_modal_forms.forms import BSModalForm

class ConfirmForm(BSModalForm):
    def __init__(self, *args, **kwargs):
        if "initial" in kwargs:
            for k,v in kwargs["initial"].items():
                self.base_fields[k]=CharField(
                    initial=v,
                    widget=HiddenInput,
                )
        super().__init__(*args, **kwargs)
        
        for f in self.fields:
            self.fields[f].disabled = True 