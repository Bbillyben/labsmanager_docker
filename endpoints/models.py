from django.db import models
from django.utils.translation import gettext_lazy as _

from labsmanager.models_utils import PERCENTAGE_VALIDATOR 
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

class endpoint(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('endpoint Name'))
    desc =  models.TextField(null=True, blank=True, verbose_name=_('endpoint desc'))
    deadline_date = models.DateField(null=True, blank=True, verbose_name=_('Deadline Date'))
    
    type_endpoint=[("o",_("one-time")), ("q", _("quantifiable"))]
    type = models.CharField(
        max_length=1,
        choices=type_endpoint,
        blank=False,
        default=type_endpoint[0][0], 
        verbose_name=_('Type'),        
    )
    quotity = models.DecimalField(max_digits=4, decimal_places=3, default=0, validators=PERCENTAGE_VALIDATOR, verbose_name=_('Completion quotity'))
    
    status=models.BooleanField(default=False, verbose_name=_('Endpoints Status'))
    
    class Meta:
        abstract = True
        
class Milestones(endpoint):
    from project.models import Project 
    from staff.models import Employee
    
    project=models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    history = AuditlogHistoryField()
    employee= models.ManyToManyField(Employee, related_query_name="milestones_by_employee", related_name="milestones")
    
    class meta:
        verbose_name = _("Milestone")
        verbose_name_plural = _("Milestones")

    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.project.name} - {self.name}"




auditlog.register(Milestones)