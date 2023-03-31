from django.forms import  DateInput
from django.forms.widgets import Input, TextInput

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