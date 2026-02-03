from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from labsmanager.models_utils import PERCENTAGE_VALIDATOR 
from labsmanager.mixin import SanitizeDataFormMixin, CachedModelMixin
from .manager import milestones_manager
from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

class endpoint(CachedModelMixin, models.Model):
    name = models.CharField(max_length=100, verbose_name=_('endpoint Name'))
    desc =  models.TextField(null=True, blank=True, verbose_name=_('endpoint desc'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('Deadline Date'))
    
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
    
    cached_vars = ['status', 'quotity']
    class Meta:
        abstract = True
    
    def is_overdue(self):
        # Vérifie si la date limite est dans le passé et si le statut est False
        return self.end_date and self.end_date < timezone.now().date() and not self.status

from labsmanager.mixin import ActiveDateMixin           
class Milestones(endpoint, ActiveDateMixin):
    '''
    Docstring for Milestones
    Milestones represent Both Milestones AND Tasks, a tasks without start date is a Milestone
    '''
    from project.models import Project 
    from staff.models import Employee
    
    objects = models.Manager()
    expired = milestones_manager()
    
    start_date=models.DateField(null=True, blank=True, verbose_name=_('Start Date'),
                                help_text=_('Leave it empty to define as milestone')
                                )
    project=models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'))
    history = AuditlogHistoryField()
    employee= models.ManyToManyField(Employee, related_query_name="milestones_by_employee", related_name="milestones", blank=True)
    
    class meta:
        verbose_name = _("Milestone")
        verbose_name_plural = _("Milestones")
    @property
    def is_milestone(self):
        return self.start_date is None
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.project.name} - {self.name}"
    

        




auditlog.register(Milestones)