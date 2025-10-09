from django.forms import  DateInput, BooleanField, CharField, HiddenInput, DecimalField
from django.forms.widgets import Input, TextInput
from django.utils.translation import gettext_lazy as _
from decimal import Decimal, ROUND_HALF_UP
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
            

class PercentageField(DecimalField):
    def __init__(self, *args, **kwargs):
           
        kwargs.setdefault('decimal_places', 1) # as a qutotity field from 0.000 to 1.000 forces digit
        kwargs.setdefault('max_digits', 4) # as a qutotity field from 0.000 to 1.000 forces digit
        
        return super().__init__(*args, **kwargs)
    def prepare_value(self, value):
        if value is None:
            return value
        return (Decimal(value) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return value
        return (Decimal(value) / 100).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


from django import forms

class ConfirmActionForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        initial=True,   # valeur par défaut
        widget=forms.HiddenInput()  # champ caché
    )