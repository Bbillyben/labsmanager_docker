from time import altzone
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models import Sum

from django.utils import timezone

from auditlog.models import AuditlogHistoryField
from auditlog.registry import auditlog

from faicon.fields import FAIconField

from labsmanager.mixin import ActiveDateMixin

### Models 
class Employee(models.Model):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Employee")
        verbose_name_plural = _("Employee")
        ordering = ['first_name']

    """Model for employee"""
    first_name=models.CharField(max_length=40, blank=False, null=False)
    last_name=models.CharField(max_length=40, blank=False, null=False)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE, verbose_name=_('User'))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_('Birth Date'))
    entry_date = models.DateField(null=True, blank=True, verbose_name=_('Entry Date'))
    exit_date = models.DateField(null=True, blank=True, verbose_name=_('Exit Date'))
    is_active=models.BooleanField(default=True, null=False)
    history = AuditlogHistoryField()
    
    @property
    def user_name(self):
        return self.first_name+" "+self.last_name
    
    @property
    def is_team_leader(self):
        teams=Team.objects.filter(leader=self.pk).values("pk")
        if teams:
            return True
        return False
    
    @property
    def is_team_mate(self):
        teams=TeamMate.objects.filter(employee=self.pk).values("pk")
        if teams:
            return True
        return False
    
    
    @property
    def get_status(self):
        return Employee_Status.objects.filter(employee=self.pk)
    
    @property
    def contracts(self):
        from expense.models import Contract
        return Contract.objects.filter(employee=self.pk)
    
    #ItemPrice.objects.aggregate(Sum('price'))
    @property
    def contracts_quotity(self):
        from expense.models import Contract
        return Contract.objects.filter(Q(employee=self.pk) &  Q(start_date__lte=timezone.now()) & ( Q(end_date__gte=timezone.now()) | Q(end_date=None))).aggregate(Sum('quotity'))["quotity__sum"]

    @property
    def projects(self):
        from project.models import Participant
        return Participant.objects.filter(employee=self.pk)
    
    @property
    def projects_quotity(self):
        from project.models import Participant
        return Participant.objects.filter(Q(employee=self.pk) & Q(project__status=True) &  Q(start_date__lte=timezone.now())  & ( Q(end_date__gte=timezone.now()) | Q(end_date=None)) ).aggregate(Sum('quotity'))["quotity__sum"]
    @property
    def info(self):
        return GenericInfo.objects.filter(employee=self.pk)
    def __str__(self):
        """Return a string representation of the Employee (for use in the admin interface)"""
        return  f"{self.first_name} {self.last_name}"



class Employee_Status(ActiveDateMixin):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Status")
        verbose_name_plural = _("Status")
        
        
    type = models.ForeignKey('Employee_type', on_delete=models.CASCADE, verbose_name=_('Type'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    contract_status=(("c",_("Contractual")), 
                ("s", _("Statutory")),
                )
    is_contractual= models.CharField(
        max_length=1,
        choices=contract_status,
        blank=False,
        default='c', verbose_name=_('Is Contractual'),
    )
    history = AuditlogHistoryField()
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.employee.first_name} {self.employee.last_name}  : {self.type.name}"
    

class Employee_Type(models.Model):
    
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Employee Type")
        ordering = ['name']
        
    shortname = models.CharField(max_length=30, verbose_name=_('Abbreviation'), unique=True)
    name = models.CharField(max_length=70, verbose_name=_('Name'), unique=True)
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.name} ({self.shortname})"

class Team(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Team")
    
    name = models.CharField(max_length=70, verbose_name=_('Team Name'))
    leader = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Team Leader'))
    history = AuditlogHistoryField()
    
    @property
    def nb_mate(self):
        mates = TeamMate.objects.filter(team=self.pk)
        if mates: return mates.count()
        return 0
    
    @property
    def team_mate(self):
        return TeamMate.objects.filter(team=self.pk)
        
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.name}"



class TeamMate(ActiveDateMixin):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("TeamMate")    
        
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name=_('Team'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))

    
    history = AuditlogHistoryField()
    
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return f"{self.team} / {self.employee}"
    
    
    
    def clean(self):
        team = self.team
        inuser = TeamMate.objects.filter(Q(employee=self.employee), Q(team=team), ~Q(pk=self.pk))
        if inuser:
            raise ValidationError(_('Already in Team'))
        isLeader = Team.objects.filter(Q(pk=self.team.pk), Q(leader=self.employee))
        if isLeader:
            raise ValidationError(_('Is Team leader'))
        

class GenericInfoType(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Type of Generic Info")
    
    name = models.CharField(max_length=50, unique=True, verbose_name=_('Name'))
    icon = FAIconField(null=True,)
    
    def __str__(self):
        """Return a string representation of the Status (for use in the admin interface)"""
        return self.name

class GenericInfo(models.Model):
    class Meta:
        """Metaclass defines extra model properties"""
        verbose_name = _("Generic Info")
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'))
    info =  models.ForeignKey(GenericInfoType, on_delete=models.CASCADE, verbose_name=_('Info Type'))
    value = models.CharField(max_length=150, blank=True, null=True, verbose_name=_('Info Value'))
    history = AuditlogHistoryField()
    
    
    
auditlog.register(Employee)
auditlog.register(Employee_Status)
auditlog.register(Team)
auditlog.register(TeamMate)
auditlog.register(GenericInfo)