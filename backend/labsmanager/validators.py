from django.core.validators import BaseValidator
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext_lazy as _

    
class RGBColorValidator(BaseValidator):
    """
    Validates whether the color is in RGB (#RRGGBB) or ARGB (#AARRGGBB) format.
    Inherits BaseValidator for advanced error handling.
    """

    # Définir une expression régulière pour valider les formats #RRGGBB et #AARRGGBB
    regex = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$'
    
    def compare(self, value, limit_value):
        return not re.match(self.regex, value)

    def clean(self, value):
        return value

    def message(self):
        return _('The color provided is invalid. Use #RRGGBB or #AARRGGBB.')

    def __call__(self, value):
        if self.compare(self.clean(value), None):
            raise ValidationError(self.message())

    
    