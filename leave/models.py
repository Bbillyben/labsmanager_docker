from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F
from django.core.exceptions import ValidationError

from labsmanager.mixin import ActiveDateMixin
from mptt.models import MPTTModel, TreeForeignKey
from datetime import timedelta
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
        verbose_name=_('Start Period'),
        max_length=2,
        choices=start_choices,
        default="ST",
    )
    end_period=models.CharField(
        verbose_name=_('End Period'),
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
        return num_open-s-e
    @property
    def return_date(self):
        if self.end_date:
            if self.end_period == "MI":
                return self.end_date + timedelta(hours=12)
            else:
                return self.end_date + timedelta(days=1)
        return None
    
    def clean(self):
        super().clean()
        if not self.start_date or not self.end_date:
            return
        start = self.start_date.toordinal() * 2 + (self.start_period == "MI")
        end = self.end_date.toordinal() * 2 + (1 if self.end_period == "MI" else 2)
        if start >= end:
            raise ValidationError({"end_date": _("End must be after start.")})
        if not self.employee_id or not self.type_id:
            return
        candidates = Leave.objects.filter(
            employee_id=self.employee_id,
            type_id=self.type_id,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(pk=self.pk).only("start_date", "start_period", "end_date", "end_period")
        for other in candidates:
            other_start = other.start_date.toordinal() * 2 + (other.start_period == "MI")
            other_end = other.end_date.toordinal() * 2 + (1 if other.end_period == "MI" else 2)
            if start < other_end and other_start < end:
                raise ValidationError({"__all__": ValidationError(
                    _("A leave of this type already overlaps this period."), code="overlap"
                )})
        
    def __str__(self):
        return f'{self.employee} - {self.type}'
    
auditlog.register(Leave)
