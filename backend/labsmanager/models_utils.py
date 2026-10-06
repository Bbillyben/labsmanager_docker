from django.core.validators import MinValueValidator, MaxValueValidator


PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(1)]
NEGATIVE_VALIDATOR = [MaxValueValidator(0)]


class PermChecker():
    perms_auth=('view', 'change', 'add', 'delete')
    
    