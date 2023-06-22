from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F

from labsmanager.mixin import ActiveDateMixin
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
    
class Leave(ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Leave")
        # unique_together = ('type', 'fund',)
    start_choices=[
        ("ST", _("start")),
        ("MI", _("midday")),
    ]
    end_choices=[
        ("MI", _("midday")),
        ("EN", _("end")),
    ]
    
    
    type=models.ForeignKey(Leave_Type, on_delete=models.CASCADE, verbose_name=_('Type'))
    employee=models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    
    start_period=models.CharField(
        max_length=2,
        choices=start_choices,
        default="ST",
    )
    end_period=models.CharField(
        max_length=2,
        choices=end_choices,
        default="EN",
    )
    comment=models.TextField(null=True, blank=True)

    history = AuditlogHistoryField()
    
    @property
    def dayCount(self):
        num_open = self.open_days
        s=0
        e=0
        if self.start_period == "MI":
            s=0.5
        if self.end_period == "MI":
            e=0.5
        print(str(num_open-s-e)+"  / "+str(self.start_period) + " - "+str(s)+" / "+str(e))
        return num_open-s-e
        
    
    def __str__(self):
        return f'{self.employee} - {self.type}'
    
auditlog.register(Leave)