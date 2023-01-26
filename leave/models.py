from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F


from mptt.models import MPTTModel, TreeForeignKey
from staff.models import Employee
# Create your models here.

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from colorfield.fields import ColorField

class Leave_Type(MPTTModel):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Leave Type")
        # ordering = ['short_name']
    
    class MPTTMeta:
        order_insertion_by = ['short_name']
                
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    short_name= models.CharField(max_length=10, verbose_name=_('Abbreviation'))
    name = models.CharField(max_length=60, verbose_name=_('Type name'))
    color=ColorField(default='#FF0000')
    def __str__(self):
        return f'{self.name}'
    
class Leave(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Leave")
        # unique_together = ('type', 'fund',)
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=F('start_date')),
                name=_("Fund End Date should be greater than start date"),
            )
        ]
        
    type=models.ForeignKey(Leave_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    start_date=models.DateField(null=False, blank=False, verbose_name=_('Start Date'))
    end_date=models.DateField(null=True, blank=True, verbose_name=_('End Date'))
    employee=models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    comment=models.TextField(null=True, blank=True)

    history = AuditlogHistoryField()
    
    
    def __str__(self):
        return f'{self.employee} - {self.type}'
    
auditlog.register(Leave)